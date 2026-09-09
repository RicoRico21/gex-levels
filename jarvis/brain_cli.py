"""Free backend: drive the Claude Code CLI instead of the paid API.

`claude -p` runs a full agent turn using the subscription you already pay for,
so there is no per-token bill. The tradeoffs are real and worth knowing:

- Turns count against your plan's usage limits, shared with your own
  interactive Claude Code use.
- Claude Code brings its own tools, so the vault works natively (Read, Write,
  Edit, Grep over the vault folder) but the Python tools in jarvis/skills/ -
  market data especially - are not available. It falls back to web search.
- This is for your own use. Anthropic does not permit offering subscription
  login to other people through a product you build.

Note the absence of `--bare`: bare mode deliberately ignores your subscription
login and demands an API key, which is the exact thing we're avoiding here.
"""

import json
import shutil
import subprocess

from . import config

TIMEOUT_SECONDS = 900
ALLOWED_TOOLS = "Read,Write,Edit,Glob,Grep,WebSearch,WebFetch"

SYSTEM = """You are Jarvis, {owner_ref} personal operator: content, daily
planning, market reads and client correspondence.

Your working directory is the vault - it is your memory, and it is plain
markdown. Use your file tools on it freely:

  inbox/log.md        running log of things captured as they happen
  daily/YYYY-MM-DD.md one note per day: the plan and how it went
  clients/<name>.md   one per client - read before writing to them
  content/voice.md    how this person writes. Read before drafting anything
                      public or client-facing. Follow it.
  content/pipeline.md what content is planned and published
  trading/journal.md  trade ideas, the thesis, and what happened

Finished drafts go in {outbox} - emails in emails/, content in content/.

How you work:
- Grep the vault before you answer. Answering from nothing when a note exists
  is the main way you fail them.
- Write things down. Anything durable you learn - a client preference, a
  decision, a result - goes into the right file. Your memory is those files.
- Prefer doing to asking. If a request is clear, produce the finished thing.

What you may and may not do:
- You DRAFT. You cannot send email, post content, or place trades, and you
  should not pretend otherwise. Write the draft to the outbox and say it's
  waiting.
- Never invent a fact about a client, a number, or a market level. Look it up
  with web search, or say you don't know. You have no live market data feed
  here, so quote prices only from a search result and say where they came from.
- On anything involving money, state the risk plainly and say what would make
  the idea wrong. You are not a licensed adviser and this is not advice.

How you write:
- Talk like a sharp colleague. No preamble, no "Certainly!", no restating the
  request back.
- Replies reach them on their phone. Short unless they asked for long. Answer
  first, caveats after."""


def available() -> bool:
    return shutil.which("claude") is not None


def _supports_permission_prompts() -> bool:
    """--permission-prompts landed in Claude Code 2.1.259."""
    try:
        raw = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=30
        ).stdout
        parts = raw.split()[0].split(".")
        return tuple(int(p) for p in parts[:3]) >= (2, 1, 259)
    except Exception:
        return False


def _context_header(owner: str) -> str:
    """Facts worth putting in front of a fresh session."""
    import datetime as _dt

    lines = [f"Today is {_dt.date.today():%A %d %B %Y}."]
    try:
        from .skills import calendar as cal

        if cal.FEED_URLS:
            # The CLI backend has no calendar tool, so fetch it here instead.
            lines.append("\nYour calendar:\n" + cal.get_calendar.call({"days": 2}))
    except Exception:
        pass
    return "\n".join(lines)


def think(user_input: str, state: dict | list | None = None, owner: str = "") -> tuple[str, dict]:
    """Run one turn through the Claude Code CLI.

    `state` carries the session id between turns; pass back what you got.
    """
    if not available():
        return (
            "The `claude` command isn't installed. Install Claude Code "
            "(npm install -g @anthropic-ai/claude-code) and run `claude` once "
            "to log in - or set ANTHROPIC_API_KEY to use the paid backend.",
            {},
        )

    config.ensure_dirs()
    session_id = state.get("session_id") if isinstance(state, dict) else None

    prompt = user_input if session_id else f"{_context_header(owner)}\n\n{user_input}"

    command = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "json",
        "--append-system-prompt",
        SYSTEM.format(
            owner_ref=f"{owner}'s" if owner else "your user's", outbox=config.OUTBOX_DIR
        ),
        "--allowedTools",
        ALLOWED_TOOLS,
        "--permission-mode",
        "acceptEdits",
        "--add-dir",
        str(config.OUTBOX_DIR),
    ]
    if _supports_permission_prompts():
        command += ["--permission-prompts", "none"]
    if session_id:
        command += ["--resume", session_id]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd=config.VAULT_DIR,
        )
    except subprocess.TimeoutExpired:
        return ("That took over 15 minutes and I stopped it. Try a narrower ask.", {})

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "no output").strip()
        if "resume" in detail.lower() or "session" in detail.lower():
            # A stale session id shouldn't wedge the conversation - start fresh.
            return think(user_input, None, owner)
        return (f"Claude Code failed: {detail[:400]}", {})

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return (completed.stdout.strip() or "(no response)", {})

    reply = (payload.get("result") or "").strip()
    new_state = {"session_id": payload.get("session_id")}
    if payload.get("is_error"):
        return (f"Claude Code reported an error: {reply[:400]}", new_state)
    return (reply or "(done - nothing to report)", new_state)
