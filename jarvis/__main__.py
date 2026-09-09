"""Entry point.

    python -m jarvis                     interactive terminal chat
    python -m jarvis "draft this week"   one-shot
    python -m jarvis --telegram          run the Telegram bot
    python -m jarvis --brief             produce the morning brief
"""

import sys

from . import brain, config
from .channels import cli

BRIEF_PROMPT = (
    "Produce my morning brief. Read today's plan and my recent notes and log, "
    "check anything market-relevant I'm tracking in the trade journal, and give "
    "me: what matters today, what's slipping, and the one thing to do first. "
    "Then write the plan into today's daily note."
)


def main(argv: list[str]) -> int:
    config.ensure_dirs()

    if argv and argv[0] == "--telegram":
        from .channels import telegram

        return telegram.run()

    if argv and argv[0] == "--brief":
        reply, _ = brain.think(BRIEF_PROMPT)
        print(reply)
        return 0

    return cli.run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
