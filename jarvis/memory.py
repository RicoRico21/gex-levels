"""The vault: plain markdown files that Jarvis reads and writes.

Deliberately not a database. Every note is a file you can open in Obsidian,
edit by hand, sync to your phone, or delete. If Jarvis ever goes away, your
memory is still sitting there in readable text.
"""

import datetime as _dt
import re
from pathlib import Path

from . import config


class VaultError(Exception):
    """Raised when a requested path escapes the vault."""


def resolve(relative_path: str, root: Path | None = None) -> Path:
    """Resolve a vault-relative path, refusing anything that escapes the vault.

    The model chooses these paths, so this check is load-bearing: without it a
    path like ``../../.ssh/id_rsa`` would be readable.
    """
    root = (root or config.VAULT_DIR).resolve()
    candidate = (root / relative_path.lstrip("/")).resolve()
    if candidate != root and root not in candidate.parents:
        raise VaultError(f"path {relative_path!r} is outside the vault")
    if candidate.suffix == "":
        candidate = candidate.with_suffix(".md")
    return candidate


def today() -> str:
    return _dt.date.today().isoformat()


def daily_note_path() -> str:
    return f"daily/{today()}.md"


def read(relative_path: str) -> str:
    path = resolve(relative_path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write(relative_path: str, content: str) -> Path:
    path = resolve(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def append(relative_path: str, content: str) -> Path:
    path = resolve(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    separator = "" if not existing or existing.endswith("\n") else "\n"
    path.write_text(existing + separator + content.rstrip() + "\n", encoding="utf-8")
    return path


def listing(folder: str = "") -> list[str]:
    root = resolve(folder) if folder else config.VAULT_DIR
    if not root.exists():
        return []
    return sorted(
        str(p.relative_to(config.VAULT_DIR))
        for p in root.rglob("*.md")
        if p.is_file()
    )


def search(query: str, limit: int = 20) -> list[tuple[str, str]]:
    """Case-insensitive substring search. Returns (path, matching line) pairs."""
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    hits: list[tuple[str, str]] = []
    for path in config.VAULT_DIR.rglob("*.md"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line in text.splitlines():
            if pattern.search(line):
                hits.append((str(path.relative_to(config.VAULT_DIR)), line.strip()))
                if len(hits) >= limit:
                    return hits
    return hits


def slugify(text: str, max_length: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:max_length].rstrip("-") or "untitled")


def timestamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
