"""Terminal front end - one-shot or interactive."""

import sys

from .. import brain


def run(argv: list[str]) -> int:
    if argv:
        reply, _ = brain.think(" ".join(argv))
        print(reply)
        return 0

    print("Jarvis - type a message, or Ctrl-D to quit.\n")
    history: list = []
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        reply, history = brain.think(line, history)
        print(f"\n{reply}\n")


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
