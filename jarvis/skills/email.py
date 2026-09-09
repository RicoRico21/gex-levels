"""Client email - drafts by default, sending only behind an explicit gate."""

import smtplib
from email.message import EmailMessage

from anthropic import beta_tool

from .. import config, memory


@beta_tool
def get_client_brief(client: str) -> str:
    """Read everything the vault knows about a client before writing to them.

    Args:
        client: The client's name, e.g. "acme" or "Jane Doe".
    """
    slug = memory.slugify(client)
    note = memory.read(f"clients/{slug}.md")
    if note:
        return note
    hits = memory.search(client)
    if hits:
        return "no client file, but these notes mention them:\n" + "\n".join(
            f"{path}: {line}" for path, line in hits
        )
    return f"(nothing on file for {client})"


@beta_tool
def draft_email(to: str, subject: str, body: str, client: str = "") -> str:
    """Write a client email to the outbox for the user to review and send.
    This does NOT send anything.

    Args:
        to: Recipient email address.
        subject: Subject line.
        body: Full plain-text body, including the sign-off.
        client: Optional client name, so the draft is filed against them.
    """
    slug = memory.slugify(f"{memory.today()}-{client or to}-{subject}")
    path = config.OUTBOX_DIR / "emails" / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"To: {to}\nSubject: {subject}\nDrafted: {memory.timestamp()}\n"
        f"Status: awaiting approval\n\n---\n\n{body.strip()}\n",
        encoding="utf-8",
    )
    if client:
        memory.append(
            f"clients/{memory.slugify(client)}.md",
            f"- {memory.timestamp()} - drafted email: {subject}",
        )
    return f"draft saved to outbox/emails/{path.name} - nothing was sent"


@beta_tool
def list_email_drafts() -> str:
    """List email drafts waiting for the user's approval."""
    folder = config.OUTBOX_DIR / "emails"
    drafts = sorted(p.name for p in folder.glob("*.md")) if folder.exists() else []
    return "\n".join(drafts) if drafts else "(no drafts waiting)"


@beta_tool
def send_email(to: str, subject: str, body: str) -> str:
    """Actually send an email. Disabled unless the user has explicitly turned
    sending on. Prefer draft_email; only call this when the user has asked for
    this specific message to go out.

    Args:
        to: Recipient email address.
        subject: Subject line.
        body: Full plain-text body.
    """
    if not config.ALLOW_EMAIL_SEND:
        return (
            "SENDING IS OFF. The email was not sent. Save it with draft_email "
            "instead and tell the user it is waiting in the outbox. (They can "
            "enable sending by setting JARVIS_ALLOW_EMAIL_SEND=true in .env.)"
        )
    if not (config.SMTP_HOST and config.SMTP_USER and config.EMAIL_FROM):
        return "sending is enabled but SMTP settings are incomplete in .env"

    message = EmailMessage()
    message["From"] = config.EMAIL_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
        server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.send_message(message)

    memory.append("inbox/log.md", f"- {memory.timestamp()} - SENT email to {to}: {subject}")
    return f"sent to {to}"


TOOLS = [get_client_brief, draft_email, list_email_drafts, send_email]
