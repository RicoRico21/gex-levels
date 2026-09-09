# Jarvis

A personal operator that writes your content, plans your day, researches and
analyses markets, and drafts your client email — then hands you the result to
approve. Runs on your machine, remembers in plain markdown, sends nothing
without you.

## The honest version of "how do I build this"

The diagram in that Instagram story is real, and it's four boxes:

| Their name | What it actually is | Here |
|---|---|---|
| "Comms — ears + voice" | A chat interface | `jarvis/channels/telegram.py` (~120 lines) |
| "Smart router — the AI agent + orchestrator" | One API call in a loop | `jarvis/brain.py` (~90 lines) |
| "Claude — the hands and brain" | The model, plus tools you wrote | `jarvis/skills/` |
| "Obsidian — the memory" | A folder of markdown files | `vault/` |

That's the whole architecture. There is no fifth secret box. The hard part was
never the wiring — it's the two things no course can give you: **the tools that
touch your actual accounts**, and **the notes that make it know your business.**
Both are in this repo as your own files, and both take you an afternoon.

The one genuinely non-obvious idea worth taking from it: **make memory a folder
of markdown, not a database.** You can open it in Obsidian, fix a wrong note by
hand, sync it to your phone, and read it when Jarvis is gone. Every "AI second
brain" that stores memory in a vector DB you can't read is worse than this.

## Setup

```bash
git clone <this repo> && cd gex-levels
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then add your ANTHROPIC_API_KEY
```

Talk to it:

```bash
python -m jarvis                                  # interactive chat
python -m jarvis "draft three X posts on gamma"   # one-shot
python -m jarvis --brief                          # morning brief
python -m jarvis --telegram                       # run the phone bot
```

For Telegram: message [@BotFather](https://t.me/botfather) → `/newbot` → put the
token in `.env` → `python -m jarvis --telegram` → message your bot. It prints
your chat id on the first message; paste that into `JARVIS_TELEGRAM_ALLOWED_IDS`
so the bot only answers you.

**Do this before anything else:** fill in `vault/content/voice.md`. Paste in
three or four of your own posts and emails. It's the difference between drafts
that sound like you and drafts that sound like ChatGPT, and it takes 20 minutes.

## What it can do

21 tools, all in `jarvis/skills/`:

- **Memory** — read, write, append and search the vault. It checks your notes
  before answering, and writes down what it learns.
- **Planning** — reads and writes the daily note, adds tasks, logs decisions.
- **Content** — reads your voice guide, drafts posts to `outbox/content/`, keeps
  a pipeline file.
- **Client email** — pulls the client's history from the vault, drafts to
  `outbox/emails/`, files a record against the client.
- **Markets** — live quotes, trend and volatility stats, and a trade journal
  that records the *thesis* and what would invalidate it, not just the levels.
- **Web search** — Anthropic-hosted, so research and current events work.

## Safety posture: it drafts, you send

This is the default and it is deliberate.

- `send_email` refuses unless you set `JARVIS_ALLOW_EMAIL_SEND=true`.
- `place_order` refuses, and no broker is connected. Turning the flag on gets
  you a message telling you to write the adapter yourself.
- Vault paths are confined — the model can't read `~/.ssh` by asking for
  `../../.ssh/id_rsa`.

An agent that emails your clients unsupervised will eventually send something
that costs you one. An LLM loop with live broker credentials will eventually
place something that costs you more. Run in draft mode for a few weeks, read
what it produces, and loosen one gate at a time once you've seen it be right
when it mattered.

Nothing here is financial advice, and the market tools are analysis, not signals.

## Adding a capability

This is the part that matters — Jarvis is only as useful as the tools you give
it. One function, one docstring:

```python
# jarvis/skills/calendar.py
from anthropic import beta_tool

@beta_tool
def next_meetings(days: int = 1) -> str:
    """Get the user's upcoming calendar events.

    Args:
        days: How many days ahead to look.
    """
    return your_calendar_lookup(days)

TOOLS = [next_meetings]
```

Then add it to the imports and the `TOOLS` list in `jarvis/skills/__init__.py`.
That's it — the docstring becomes the schema the model sees, so write it for a
smart new hire: say what the tool is *for* and when to reach for it.

## Where to take it next

Roughly in order of payoff:

1. **Fill the vault.** Voice guide, one note per client, your trading rules. The
   agent's quality is mostly a function of what it knows about you.
2. **Real calendar** — Google Calendar API into a `calendar.py` skill, so the
   daily plan works around actual meetings.
3. **Run it on a schedule** — cron `--brief` at 7am and a market scan at the
   open. This is when it stops being a chatbot and starts being staff.
4. **Voice notes** — Telegram gives you the audio file; run it through a
   speech-to-text API and feed the transcript to `brain.think()`. The plumbing
   is already there in `telegram.py`.
5. **Put it on a $5 VPS** so it's awake when your laptop isn't.

## Layout

```
jarvis/
  brain.py           the agent loop: Claude + every tool, with history
  config.py          env, paths, safety gates
  memory.py          vault file operations, with path confinement
  channels/          telegram.py, cli.py
  skills/            notes, schedule, content, email, trading
vault/               memory: plain markdown, yours to edit
outbox/              drafts awaiting your approval
```
