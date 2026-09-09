"""`python -m jarvis --doctor` - tells you exactly what is and isn't working.

Every failure line ends with the specific thing to do about it. Run this
whenever something doesn't work; it's faster than reading a stack trace.
"""

import os
import sys
from pathlib import Path

from . import config

OK, BAD, WARN = "  ok  ", " FAIL ", " todo "


def _line(status: str, label: str, detail: str = "") -> None:
    print(f"[{status}] {label}" + (f"\n         {detail}" if detail else ""))


def _check_python() -> bool:
    good = sys.version_info >= (3, 11)
    _line(
        OK if good else BAD,
        f"Python {sys.version_info.major}.{sys.version_info.minor}",
        "" if good else "Jarvis needs Python 3.11+. Install a newer Python and rebuild the venv.",
    )
    return good


def _check_packages() -> bool:
    required = {
        "anthropic": "the Claude SDK",
        "dotenv": "reads your .env",
        "requests": "HTTP",
    }
    optional = {
        "yfinance": "market data (trading tools)",
        "icalendar": "calendar feeds",
        "recurring_ical_events": "repeating calendar events",
    }
    good = True
    for module, why in required.items():
        try:
            __import__(module)
            _line(OK, f"{module} installed ({why})")
        except ImportError:
            good = False
            _line(BAD, f"{module} missing ({why})", "Run: pip install -r requirements.txt")
    for module, why in optional.items():
        try:
            __import__(module)
            _line(OK, f"{module} installed ({why})")
        except ImportError:
            _line(WARN, f"{module} missing - {why} will be unavailable",
                  "Run: pip install -r requirements.txt")
    return good


def _check_env_file() -> bool:
    env = config.ROOT / ".env"
    if env.exists():
        _line(OK, ".env exists")
        return True
    _line(BAD, ".env missing", "Run: cp .env.example .env   then add your API key")
    return False


def _check_anthropic() -> bool:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        _line(BAD, "ANTHROPIC_API_KEY not set",
              "Get one at console.anthropic.com/settings/keys and put it in .env")
        return False
    try:
        import anthropic

        anthropic.Anthropic().models.retrieve(config.MODEL)
    except Exception as exc:
        _line(BAD, f"Claude API key rejected or unreachable ({type(exc).__name__})", str(exc)[:160])
        return False
    _line(OK, f"Claude API works, model {config.MODEL} available")
    return True


def _check_telegram() -> bool:
    if not config.TELEGRAM_BOT_TOKEN:
        _line(WARN, "Telegram not set up - CLI still works",
              "Message @BotFather, /newbot, put the token in .env as TELEGRAM_BOT_TOKEN")
        return True
    try:
        import requests

        result = requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getMe", timeout=15
        ).json()
    except Exception as exc:
        _line(BAD, "Could not reach Telegram", str(exc)[:160])
        return False
    if not result.get("ok"):
        _line(BAD, "Telegram rejected the bot token",
              "Check TELEGRAM_BOT_TOKEN in .env matches what @BotFather gave you")
        return False
    _line(OK, f"Telegram bot @{result['result'].get('username')} reachable")
    if not config.TELEGRAM_ALLOWED_IDS:
        _line(WARN, "Bot answers ANYONE who messages it",
              "Run --telegram, message the bot, and put the chat id it prints into "
              "JARVIS_TELEGRAM_ALLOWED_IDS")
    else:
        _line(OK, f"Bot locked to {len(config.TELEGRAM_ALLOWED_IDS)} chat id(s)")
    return True


def _check_calendar() -> bool:
    from .skills import calendar as cal

    if not cal.FEED_URLS:
        _line(WARN, "No calendar connected",
              "Add your calendar's private ICS URL to JARVIS_CALENDAR_ICS_URLS (SETUP.md step 6)")
        return True
    for url in cal.FEED_URLS:
        try:
            cal._fetch(url)
            _line(OK, f"Calendar feed reachable ({url[:45]}...)")
        except Exception as exc:
            _line(BAD, "Calendar feed unreachable", f"{url[:60]}... -> {str(exc)[:100]}")
            return False
    return True


def _check_voice() -> bool:
    from . import transcribe

    if transcribe.available():
        _line(OK, f"Voice notes on (via {transcribe.BASE_URL})")
    else:
        _line(WARN, "Voice notes off - text still works",
              "Set JARVIS_STT_API_KEY in .env (SETUP.md step 7)")
    return True


def _check_vault() -> bool:
    config.ensure_dirs()
    _line(OK, f"Vault at {config.VAULT_DIR}")
    voice = config.VAULT_DIR / "content" / "voice.md"
    filled = voice.exists() and "<!--" not in voice.read_text(encoding="utf-8")
    _line(
        OK if filled else WARN,
        "Voice guide written" if filled else "Voice guide is still the blank template",
        "" if filled else "Run: python -m jarvis --onboard   (biggest quality win available)",
    )
    return True


def _check_gates() -> bool:
    _line(
        OK,
        f"Email sending: {'ON - it can email people' if config.ALLOW_EMAIL_SEND else 'OFF (drafts only)'}",
    )
    _line(
        OK,
        f"Live trading:  {'ON - check your broker adapter' if config.ALLOW_LIVE_TRADES else 'OFF (journal only)'}",
    )
    return True


def run() -> int:
    print("\nJarvis setup check\n" + "-" * 60)
    essential = [
        _check_python(),
        _check_packages(),
        _check_env_file(),
        _check_anthropic(),
    ]
    print()
    _check_telegram()
    _check_calendar()
    _check_voice()
    _check_vault()
    _check_gates()

    print("-" * 60)
    if all(essential):
        print("Ready. Try:  python -m jarvis \"what can you do?\"\n")
        return 0
    print("Fix the FAIL lines above, then run --doctor again.\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(run())
