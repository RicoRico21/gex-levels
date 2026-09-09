# Jarvis

A personal operator that plans your day around your real calendar, writes your
content in your voice, researches and analyses markets, and drafts your client
email — then hands you the result to approve. Runs on your machine, remembers in
plain markdown, sends nothing without you.

**New here? Go to [SETUP.md](SETUP.md).** It assumes you've never written Python
and takes about an hour.

**It runs free on a Claude subscription.** Jarvis has two backends: the
pay-as-you-go API, or the Claude Code CLI, which signs in with the subscription
you already pay for and costs nothing per token. It picks the free one
automatically when there's no API key. [SETUP.md step 4](SETUP.md#4-give-it-a-brain--free-or-paid)
covers the tradeoff — the short version is that free turns count against your
plan's usage limits and the Python market-data tools don't run there.

## The honest version of "how do I build this"

The architecture people sell courses on is four boxes:

| Their name | What it actually is | Here |
|---|---|---|
| "Comms — ears + voice" | A Telegram bot | `jarvis/channels/telegram.py` |
| "Smart router — AI agent + orchestrator" | One API call in a loop | `jarvis/brain.py` |
| "Claude — the hands and brain" | The model, plus tools you wrote | `jarvis/skills/` |
| "Obsidian — the memory" | A folder of markdown files | `vault/` |

There's no fifth secret box. The hard part was never the wiring — it's the two
things nobody can hand you: **the tools that touch your actual accounts**, and
**the notes that make it know your business.** Both are your own files here.

The one genuinely good idea worth taking: **make memory a folder of markdown,
not a database.** You can open it, fix a wrong note by hand, sync it to your
phone, and read it when the agent is gone. Every "AI second brain" that hides
memory in a vector DB you can't read is worse than this.

## Commands

```bash
python -m jarvis                              # interactive chat
python -m jarvis "draft three posts on GEX"   # one-shot
python -m jarvis --telegram                   # phone bot (text + voice notes)
python -m jarvis --schedule                   # run the jobs in jobs.toml
python -m jarvis --run-job "morning brief"    # run one job now
python -m jarvis --brief                      # morning brief, once
python -m jarvis --onboard                    # interview that fills the vault
python -m jarvis --doctor                     # what's set up and what isn't
```

## What it can do

23 tools in `jarvis/skills/`, plus Anthropic-hosted web search:

- **Memory** — reads, writes and searches the vault. Checks your notes before
  answering, and writes down what it learns.
- **Calendar** — reads your real calendar over an ICS feed, and finds the gaps
  big enough for focused work. Read-only by design.
- **Planning** — daily notes, tasks, a decision log, a morning brief that plans
  around the meetings you actually have.
- **Content** — reads your voice guide, drafts posts to `outbox/content/`.
- **Client email** — pulls the client's history from the vault, drafts to
  `outbox/emails/`, files a record against them.
- **Markets** — quotes, trend and volatility stats, and a journal that records
  the *thesis* and what would invalidate it, not just the levels.

It runs on a schedule (`jobs.toml`), takes voice notes on Telegram, and will
live on a $5 VPS (`deploy/`).

## Safety posture: it drafts, you send

Deliberate, and the default.

- `send_email` refuses unless you set `JARVIS_ALLOW_EMAIL_SEND=true`.
- `place_order` refuses, and no broker is connected. Flipping the flag gets you
  a message telling you to write the adapter yourself.
- Vault paths are confined — the model can't read `~/.ssh` by asking for
  `../../.ssh/id_rsa`.
- The Telegram bot can be locked to your chat id, and the doctor nags you until
  it is.

An agent that emails your clients unsupervised will eventually send something
that costs you one. An LLM loop holding live broker credentials will eventually
place something that costs more. Run it in draft mode for a few weeks, read what
it produces, and loosen one gate at a time once you've seen it be right when it
mattered.

Nothing here is financial advice, and the market tools are analysis, not signals.

## Adding a capability

This is the part that matters — Jarvis is only as useful as the tools you give
it. One function, one docstring:

```python
# jarvis/skills/invoicing.py
from anthropic import beta_tool

@beta_tool
def unpaid_invoices(days_overdue: int = 0) -> str:
    """List invoices the user hasn't been paid for.

    Args:
        days_overdue: Only show invoices at least this many days late.
    """
    return your_lookup(days_overdue)

TOOLS = [unpaid_invoices]
```

Then add it to the imports and the `TOOLS` list in `jarvis/skills/__init__.py`.
The docstring becomes the schema the model sees, so write it for a smart new
hire: say what the tool is *for* and when to reach for it.

Scheduled work is the same idea without code — add a `[[job]]` block to
`jobs.toml`.

## Layout

```
jarvis/
  brain.py         the agent loop: Claude + every tool, with history
  brain_cli.py     the free backend: drives Claude Code on your subscription
  scheduler.py     runs jobs.toml, catches up on what it missed
  onboard.py       the interview that fills the vault
  setup_check.py   --doctor
  transcribe.py    voice notes, via any OpenAI-compatible STT endpoint
  memory.py        vault file operations, with path confinement
  channels/        telegram.py, cli.py
  skills/          notes, schedule, calendar, content, email, trading
jobs.toml          scheduled work - plain text, no code
vault/             memory: plain markdown, yours to edit
outbox/            drafts awaiting your approval
deploy/            systemd units + VPS guide
```
