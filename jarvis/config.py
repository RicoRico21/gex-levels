"""Configuration, loaded once from the environment."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent


def _path(env_var: str, default: str) -> Path:
    p = Path(os.getenv(env_var, default)).expanduser()
    return p if p.is_absolute() else (ROOT / p).resolve()


def _flag(env_var: str, default: bool = False) -> bool:
    return os.getenv(env_var, str(default)).strip().lower() in ("1", "true", "yes", "on")


VAULT_DIR = _path("JARVIS_VAULT_DIR", "./vault")
OUTBOX_DIR = _path("JARVIS_OUTBOX_DIR", "./outbox")

MODEL = os.getenv("JARVIS_MODEL", "claude-opus-5")
EFFORT = os.getenv("JARVIS_EFFORT", "high")
MAX_TOKENS = int(os.getenv("JARVIS_MAX_TOKENS", "16000"))

# Safety gates. Everything Jarvis produces is a draft until you flip these.
ALLOW_EMAIL_SEND = _flag("JARVIS_ALLOW_EMAIL_SEND")
ALLOW_LIVE_TRADES = _flag("JARVIS_ALLOW_LIVE_TRADES")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_ALLOWED_IDS = {
    part.strip()
    for part in os.getenv("JARVIS_TELEGRAM_ALLOWED_IDS", "").split(",")
    if part.strip()
}

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")


def ensure_dirs() -> None:
    """Create the vault and outbox layout if it isn't there yet."""
    for sub in ("inbox", "daily", "clients", "content", "trading"):
        (VAULT_DIR / sub).mkdir(parents=True, exist_ok=True)
    for sub in ("emails", "content"):
        (OUTBOX_DIR / sub).mkdir(parents=True, exist_ok=True)
