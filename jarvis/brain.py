"""The loop: send the user's message to Claude with every tool attached, let it
work, hand back what it said."""

import datetime as _dt

import anthropic

from . import config, skills

MAX_PAUSE_RESTARTS = 5

SYSTEM = """You are Jarvis, {owner_ref} personal operator. You run content
production, daily planning, market analysis and client correspondence.

Today is {today}.

How you work:
- Check the vault before you answer. note_search and note_read hold everything
  you know about this person's clients, voice, past decisions and open threads.
  Answering from nothing when a note exists is the main way you fail them.
- Check the calendar before planning a day or proposing a time. get_calendar
  and find_free_slots read their real schedule; never guess at it, and never
  plan deep work over a meeting that's already there.
- Write things down. When you learn something durable - a client's preference, a
  decision, a result - put it in the vault. Your memory is those files and
  nothing else; anything you don't write down is gone when this chat ends.
- Prefer doing to asking. If a request is clear, produce the finished thing. Ask
  only when two readings would lead to genuinely different work.

What you may and may not do:
- You DRAFT. You do not send, post, or trade. Emails go to the outbox, content
  goes to the outbox, trades go to the journal. The user presses the button.
- Never invent a fact about a client, a number, or a market level. If you don't
  know it, look it up with web_search or the market tools, or say you don't know.
- On anything involving money, state the risk plainly and say what would make
  the idea wrong. You are not a licensed adviser and this is not advice.

How you write:
- Talk like a sharp colleague, not an assistant. No preamble, no "Certainly!",
  no restating the request back.
- Replies reach the user on their phone. Keep them short unless they asked for a
  long thing. Put the answer first and the caveats after.
"""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def system_prompt(owner: str = "") -> str:
    return SYSTEM.format(
        owner_ref=f"{owner}'s" if owner else "your user's",
        today=_dt.date.today().strftime("%A %d %B %Y"),
    )


def _runner_kwargs(messages: list, owner: str) -> dict:
    return {
        "model": config.MODEL,
        "max_tokens": config.MAX_TOKENS,
        "system": [
            {
                "type": "text",
                "text": system_prompt(owner),
                # Cache the stable prefix - it's identical on every turn.
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "tools": skills.TOOLS,
        "messages": messages,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": config.EFFORT},
    }


def _start_runner(client: anthropic.Anthropic, kwargs: dict):
    """Start a tool runner, opting into server-side refusal fallbacks when the
    installed SDK supports them."""
    try:
        return client.beta.messages.tool_runner(
            **kwargs,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except TypeError:
        # Older SDK without the fallbacks parameter - run without it.
        return client.beta.messages.tool_runner(**kwargs)


def _text_of(message) -> str:
    return "\n".join(
        block.text for block in message.content if getattr(block, "type", "") == "text"
    ).strip()


def think(user_input: str, history: list | None = None, owner: str = "") -> tuple[str, list]:
    """Run one turn. Returns (reply text, updated history).

    Pass the returned history back in on the next call to continue the
    conversation.
    """
    config.ensure_dirs()
    client = _client()
    messages = list(history or []) + [{"role": "user", "content": user_input}]

    last = None
    for _ in range(MAX_PAUSE_RESTARTS + 1):
        runner = _start_runner(client, _runner_kwargs(messages, owner))
        for message in runner:
            last = message
            # Mirror the history: the runner keeps its own copy and doesn't
            # expose it, and we need it both to resume and to continue the chat.
            messages.append({"role": "assistant", "content": message.content})
            tool_response = runner.generate_tool_call_response()
            if tool_response is not None:
                messages.append(tool_response)
        if last is None or last.stop_reason != "pause_turn":
            break
    else:
        return ("That turn kept pausing on a long search and I gave up. Try a narrower ask.", messages)

    if last is None:
        return ("Something went wrong - no response came back.", messages)
    if last.stop_reason == "refusal":
        return ("I can't help with that one.", messages)

    return (_text_of(last) or "(done - nothing to report)", messages)
