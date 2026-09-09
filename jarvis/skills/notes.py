"""Memory tools - how Jarvis reads and writes its own long-term notes."""

from anthropic import beta_tool

from .. import memory


@beta_tool
def note_read(path: str) -> str:
    """Read a note from the vault.

    Args:
        path: Vault-relative path, e.g. "clients/acme.md" or "daily/2026-09-09.md".
    """
    content = memory.read(path)
    return content or f"(no note at {path} yet)"


@beta_tool
def note_write(path: str, content: str) -> str:
    """Create or completely overwrite a note. Use note_append to add to an
    existing note without destroying it.

    Args:
        path: Vault-relative path, e.g. "clients/acme.md".
        content: Full markdown body of the note.
    """
    written = memory.write(path, content)
    return f"wrote {written.name} ({len(content)} chars)"


@beta_tool
def note_append(path: str, content: str) -> str:
    """Append a block of markdown to the end of a note, creating it if needed.

    Args:
        path: Vault-relative path.
        content: Markdown to append.
    """
    memory.append(path, content)
    return f"appended to {path}"


@beta_tool
def note_search(query: str) -> str:
    """Search every note in the vault for a phrase. Use this before answering
    anything about the user's clients, past work, preferences or decisions.

    Args:
        query: Text to look for, e.g. a client name or a ticker.
    """
    hits = memory.search(query)
    if not hits:
        return f"no notes mention {query!r}"
    return "\n".join(f"{path}: {line}" for path, line in hits)


@beta_tool
def note_list(folder: str = "") -> str:
    """List note paths in the vault.

    Args:
        folder: Optional subfolder to limit the listing, e.g. "clients".
    """
    paths = memory.listing(folder)
    return "\n".join(paths) if paths else "(vault is empty)"


TOOLS = [note_read, note_write, note_append, note_search, note_list]
