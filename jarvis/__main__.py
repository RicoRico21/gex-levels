"""Entry point.

    python -m jarvis                      interactive terminal chat
    python -m jarvis "draft this week"    one-shot
    python -m jarvis --telegram           run the Telegram bot
    python -m jarvis --schedule           run scheduled jobs from jobs.toml
    python -m jarvis --run-job NAME       run one scheduled job right now
    python -m jarvis --brief              produce the morning brief
    python -m jarvis --onboard            interview that fills the vault
    python -m jarvis --doctor             check what is and isn't set up
"""

import sys

from . import brain, config
from .channels import cli

BRIEF_PROMPT = (
    "Produce my morning brief. Read my calendar for today, today's plan, my "
    "recent notes and log, and anything open in the trade journal. Give me: "
    "what matters today, what's slipping, and the one thing to do first. Then "
    "write the plan into today's daily note."
)

USAGE = __doc__


def main(argv: list[str]) -> int:
    command = argv[0] if argv else ""

    if command in ("--help", "-h"):
        print(USAGE)
        return 0

    if command == "--doctor":
        from . import setup_check

        return setup_check.run()

    if command == "--onboard":
        from . import onboard

        return onboard.run()

    config.ensure_dirs()

    if command == "--telegram":
        from .channels import telegram

        return telegram.run()

    if command == "--schedule":
        from . import scheduler

        return scheduler.run()

    if command == "--run-job":
        from . import scheduler

        if len(argv) < 2:
            print('Which job? e.g. python -m jarvis --run-job "morning brief"')
            return 1
        return scheduler.run_named(" ".join(argv[1:]))

    if command == "--brief":
        reply, _ = brain.think(BRIEF_PROMPT)
        print(reply)
        return 0

    if command.startswith("--"):
        print(f"Unknown option {command!r}\n{USAGE}")
        return 1

    return cli.run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
