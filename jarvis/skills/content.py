"""Content production - drafts land in outbox/content/ for you to approve."""

from anthropic import beta_tool

from .. import config, memory

VOICE_NOTE = "content/voice.md"


@beta_tool
def get_voice_guide() -> str:
    """Read the user's brand voice guide - tone, audience, topics they cover and
    phrasings they refuse to use. Read this before writing anything public.
    """
    guide = memory.read(VOICE_NOTE)
    return guide or (
        "(no voice guide yet - vault/content/voice.md is empty). Ask the user "
        "for a few examples of their own posts, then write the guide yourself "
        "with note_write so future drafts sound like them."
    )


@beta_tool
def save_content_draft(title: str, platform: str, body: str) -> str:
    """Save a finished content draft for the user to review and post.

    Args:
        title: Short title, used for the filename.
        platform: Where it's going, e.g. "x", "linkedin", "newsletter", "youtube".
        body: The full draft, ready to post.
    """
    slug = memory.slugify(f"{memory.today()}-{platform}-{title}")
    path = config.OUTBOX_DIR / "content" / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# {title}\n\n- platform: {platform}\n- drafted: {memory.timestamp()}\n"
        f"- status: awaiting approval\n\n---\n\n{body.strip()}\n",
        encoding="utf-8",
    )
    memory.append(
        "content/pipeline.md", f"- [ ] {memory.today()} | {platform} | {title}"
    )
    return f"draft saved to outbox/content/{path.name} - not posted anywhere"


@beta_tool
def list_content_drafts() -> str:
    """List content drafts waiting for the user's approval."""
    folder = config.OUTBOX_DIR / "content"
    drafts = sorted(p.name for p in folder.glob("*.md")) if folder.exists() else []
    return "\n".join(drafts) if drafts else "(no drafts waiting)"


TOOLS = [get_voice_guide, save_content_draft, list_content_drafts]
