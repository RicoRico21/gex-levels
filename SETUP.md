# Setting up Jarvis from scratch

Assumes you have nothing installed and haven't written Python before. Follow it
top to bottom; each step ends with something you can check. Budget about an hour
for steps 1–6, which is the point where it becomes genuinely useful. Steps 7–11
are optional and can wait for another day.

Wherever you see `python`, use `python3` on macOS/Linux.

---

## 1. Install Python

**macOS** — open Terminal (Cmd+Space, type "terminal"):

```bash
xcode-select --install                                    # if you've never used the terminal
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.12 git
```

**Windows** — install [Python](https://www.python.org/downloads/) and tick
**"Add python.exe to PATH"** on the first screen. This is the step everyone
skips and then nothing works. Also install [Git](https://git-scm.com/download/win).
Then open PowerShell.

**Check it:**

```bash
python3 --version     # must say 3.11 or higher
```

## 2. Get the code

```bash
git clone https://github.com/RicoRico21/gex-levels.git
cd gex-levels
git checkout claude/jarvis-content-trading-assistant-xau7fq
```

## 3. Create the environment

A virtual environment keeps Jarvis's packages from colliding with anything else
on your machine. You need to activate it in every new terminal window.

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell refuses with an execution-policy error:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then try again.

**Check it:** your prompt now starts with `(.venv)`.

## 4. Get an API key

1. Go to [console.anthropic.com](https://console.anthropic.com) and sign up.
2. **Billing → add a payment method**, and put $20 on it. Without credit the key
   exists but every call fails, which is a confusing way to start.
3. **API keys → Create key**, and copy it. You only get to see it once.

Now create your config file:

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

Open `.env` in any text editor and paste the key after `ANTHROPIC_API_KEY=`.
No quotes, no spaces around the `=`.

`.env` holds live keys. It's already gitignored — never commit it, never paste
it into a chat, and rotate it in the console if you ever do.

## 5. First run

```bash
python -m jarvis --doctor
```

This checks everything and tells you exactly what to fix. Get the `FAIL` lines
to zero — `todo` lines are optional features you haven't set up yet.

Then talk to it:

```bash
python -m jarvis "what can you do?"
python -m jarvis                        # interactive; Ctrl-D to quit
```

## 6. Teach it who you are ← the step that actually matters

```bash
python -m jarvis --onboard
```

Six questions. When it asks for writing samples, **paste real things you've
written** — three to five posts or client emails. Not a description of your
style, the actual text. It turns those into `vault/content/voice.md`, which it
reads before drafting anything in your name.

Then open `vault/content/voice.md` and correct whatever it got wrong. Fill in
the client notes it created — what they hired you for, how they like to be
talked to.

This is the difference between drafts that sound like you and drafts that sound
like ChatGPT. Everything else in this document is plumbing; this is the part
that decides whether the thing is any good.

---

Everything below is optional.

---

## 7. Telegram, so it's on your phone

1. Open Telegram, message [@BotFather](https://t.me/botfather), send `/newbot`.
2. Pick a name and a username ending in `bot`.
3. Copy the token into `.env` as `TELEGRAM_BOT_TOKEN=`.

```bash
python -m jarvis --telegram
```

Message your bot. The terminal prints your chat id — put it in `.env` as
`JARVIS_TELEGRAM_ALLOWED_IDS=123456789` and restart, so the bot only answers
you. **Do this before leaving it running**: until you do, anyone who finds the
bot can use your API credit and read your notes.

## 8. Your real calendar

Read-only, no Google Cloud project needed.

**Google Calendar** → Settings → click your calendar in the left sidebar →
scroll to **"Secret address in iCal format"** → copy.
**Apple** → Calendar → right-click the calendar → Share → Public Calendar → copy
(change `webcal://` to `https://`).
**Outlook** → Settings → Calendar → Shared calendars → Publish → ICS link.

Paste it into `.env` as `JARVIS_CALENDAR_ICS_URLS=`. Comma-separate several.

That URL is a password — anyone with it can read your calendar. Keep it in
`.env` only.

```bash
python -m jarvis "what does my day look like, and when's my best focus block?"
```

Jarvis can now read your schedule but not change it. Writing to a calendar needs
full Google OAuth; add it as a `calendar_create_event` tool if you ever need it.

## 9. Voice notes

Anthropic doesn't do speech-to-text, so this points at any OpenAI-compatible
transcription endpoint. [Groq](https://console.groq.com) is the cheap fast one:

```bash
JARVIS_STT_BASE_URL=https://api.groq.com/openai/v1
JARVIS_STT_API_KEY=gsk_...
JARVIS_STT_MODEL=whisper-large-v3-turbo
```

Or OpenAI (`https://api.openai.com/v1`, `whisper-1`), or a local whisper server
if you'd rather no audio left your machine. Restart the bot and send it a voice
note.

## 10. Make it run on its own

This is when it stops being a chatbot and starts being staff.

```bash
python -m jarvis --run-job "morning brief"     # test one now
python -m jarvis --schedule                    # run the schedule
```

Jobs live in `jobs.toml` — plain text, edit freely, no code. Four are set up:
morning brief at 07:00, pre-market scan at 09:15, weekly content on Sunday
evening, and an evening review that writes up your day.

The scheduler catches up on jobs it missed while your laptop was shut, within
four hours. To have it running when your laptop isn't, see `deploy/README.md`.

## 11. Obsidian, to read the vault properly

Optional — the vault is just markdown and any editor opens it. But
[Obsidian](https://obsidian.md) is free, and "Open folder as vault" → pick
`vault/` gives you search, backlinks and a phone app. Put the folder in
iCloud/Dropbox and your notes sync everywhere, with Jarvis writing into the same
files.

---

## What it costs

Per Claude API pricing at the time of writing (Opus 5, $5/M input and $25/M
output tokens): a chat turn is somewhere under a cent; a job that reads your
vault, searches the web and drafts something runs a few cents. The four
scheduled jobs, plus normal daily use, lands in the region of $10–30/month.
Set a spend limit in the console under Billing → Limits so it can't surprise
you. If it's more than you want, `JARVIS_MODEL=claude-sonnet-5` in `.env` is
roughly 2.5x cheaper and still good.

## When something breaks

**Run `python -m jarvis --doctor` first.** It catches most of it.

| What you see | What it is |
|---|---|
| `command not found: python3` | Python isn't installed, or on Windows you didn't tick "Add to PATH" — reinstall |
| `No module named jarvis` | You're in the wrong folder. `cd` into `gex-levels` |
| `No module named anthropic` | The venv isn't active — rerun the activate line from step 3 |
| `401` / `authentication_error` | Bad key in `.env`, or you copied it with a stray space |
| `credit balance is too low` | Add money in the console under Billing |
| Bot doesn't reply | Is `python -m jarvis --telegram` still running in a terminal? It stops when you close the window |
| Jobs never fire | Is `--schedule` running? Is the machine's clock in the right timezone? |
| Drafts don't sound like you | `vault/content/voice.md` is thin. Add more real samples |

## Where things live

```
jarvis/          the code
  brain.py         the agent loop
  skills/          the tools - add capabilities here
  channels/        telegram, cli
jobs.toml        scheduled work - edit this, not code
vault/           its memory: plain markdown, yours to edit
outbox/          drafts waiting for you to send or post
deploy/          running it 24/7 on a server
.env             your keys - never commit this
```
