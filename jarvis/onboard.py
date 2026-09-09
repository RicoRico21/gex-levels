"""`python -m jarvis --onboard` - a short interview that fills the vault.

Jarvis is only as good as what it knows about you. This asks the handful of
questions that matter, then uses Claude to turn your answers into the notes it
will read for the rest of its life. Twenty minutes here beats any amount of
prompt tweaking later.
"""

import anthropic

from . import config, memory

SYNTHESIS_SYSTEM = """You are writing a voice guide that another AI will read
before drafting anything in this person's name.

Write it as markdown with these sections: Who I am, Who I'm talking to, How I
sound, Topics I cover, Never, Formats.

Rules:
- The writing samples are the most important input. Infer concrete, checkable
  rules from them: sentence length, whether they use questions, how they open
  and close, punctuation habits, how technical they get, whether they use
  emoji, first person vs second person.
- Be specific enough to be falsifiable. "Conversational but authoritative" is
  useless. "Opens with a claim, never a question. Two to three sentences per
  paragraph. Never uses exclamation marks." is useful.
- Quote two or three short phrases from the samples as anchors.
- Do not invent anything the person did not tell you or demonstrate.
- No preamble. Output the markdown document only."""


def _ask(question: str, hint: str = "") -> str:
    print(f"\n{question}")
    if hint:
        print(f"  ({hint})")
    return input("> ").strip()


def _ask_long(question: str) -> str:
    print(f"\n{question}")
    print("  (paste as much as you like, then type END on its own line)")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip().upper() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def run() -> int:
    config.ensure_dirs()
    print("""
Jarvis onboarding
-----------------
Six questions. The samples matter most - paste real posts and emails you've
written, not a description of them. Ctrl-C to bail; nothing is saved until the
end.""")

    try:
        who = _ask("What do you do, and who for?", "one or two sentences")
        audience = _ask("Who reads your stuff?", "be specific - what do they already know?")
        topics = _ask("What 3-5 topics do you want to be known for?")
        never = _ask("What should Jarvis never say or do in your name?",
                     "phrasings you hate, claims you won't make")
        samples = _ask_long("Paste 3-5 things you've written - posts, emails, anything.")
        clients = _ask("Name your current clients, comma separated.", "or press enter to skip")
    except (KeyboardInterrupt, EOFError):
        print("\n\nStopped. Nothing was written.")
        return 1

    if not samples:
        print("\nNo samples given, so the guide would be guesswork. Re-run when you have some.")
        return 1

    print("\nWriting your voice guide...")
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=config.MODEL,
        max_tokens=4000,
        system=SYNTHESIS_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"What I do: {who}\n\nMy audience: {audience}\n\n"
                    f"My topics: {topics}\n\nNever: {never}\n\n"
                    f"Writing samples:\n\n{samples}"
                ),
            }
        ],
    )
    guide = "\n".join(b.text for b in response.content if b.type == "text").strip()
    memory.write("content/voice.md", guide + "\n")
    print(f"  wrote {config.VAULT_DIR / 'content' / 'voice.md'}")

    for name in (c.strip() for c in clients.split(",") if c.strip()):
        path = f"clients/{memory.slugify(name)}.md"
        if memory.read(path):
            continue
        memory.write(
            path,
            f"# {name}\n\n## What they hired me for\n\n## How they like to be talked to\n\n"
            f"## Open threads\n\n## History\n- {memory.timestamp()} - added during onboarding\n",
        )
        print(f"  wrote {path}")

    memory.append(
        "inbox/log.md",
        f"- {memory.timestamp()} - onboarding completed. Voice guide written from "
        f"{len(samples.split())} words of samples.",
    )

    print("""
Done. Two things worth doing now:

  1. Open vault/content/voice.md and correct anything it got wrong about you.
     It's a draft of your voice, not gospel.
  2. Fill in the client notes - what they hired you for, how they like to be
     talked to. That's what makes the client emails good.

Then:  python -m jarvis "draft an X post about what I do"
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
