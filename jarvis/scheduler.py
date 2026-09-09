"""Runs jobs from jobs.toml on a schedule.

Deliberately a plain loop rather than cron: it survives a closed laptop by
catching up on jobs it missed, it keeps its own state so a restart doesn't
re-run the morning brief four times, and it works identically on macOS, Windows
and a Linux VPS. `python -m jarvis --schedule` and leave it running.
"""

import datetime as _dt
import json
import time
import tomllib
from pathlib import Path

from . import brain, config, memory

JOBS_FILE = config.ROOT / "jobs.toml"
STATE_FILE = config.VAULT_DIR / ".jarvis" / "scheduler.json"
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
TICK_SECONDS = 30
# If the machine was asleep at 07:00, still run the brief when it wakes - but
# not if it's already the evening.
DEFAULT_CATCH_UP_HOURS = 4


def load_jobs() -> list[dict]:
    if not JOBS_FILE.exists():
        return []
    with JOBS_FILE.open("rb") as handle:
        return tomllib.load(handle).get("job", [])


def _state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _record(name: str, when: _dt.datetime) -> None:
    state = _state()
    state[name] = when.isoformat()
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _already_ran_today(name: str, now: _dt.datetime) -> bool:
    stamp = _state().get(name)
    if not stamp:
        return False
    try:
        return _dt.datetime.fromisoformat(stamp).date() == now.date()
    except ValueError:
        return False


def due(job: dict, now: _dt.datetime) -> bool:
    """Is this job due right now, or was it missed recently enough to catch up?"""
    days = [d.lower() for d in job.get("days", DAYS)]
    if DAYS[now.weekday()] not in days:
        return False
    if _already_ran_today(job["name"], now):
        return False
    try:
        scheduled = _dt.time.fromisoformat(job["at"])
    except (KeyError, ValueError):
        return False
    scheduled_today = now.replace(
        hour=scheduled.hour, minute=scheduled.minute, second=0, microsecond=0
    )
    if now < scheduled_today:
        return False
    catch_up = job.get("catch_up_hours", DEFAULT_CATCH_UP_HOURS)
    return (now - scheduled_today) <= _dt.timedelta(hours=catch_up)


def _notify(text: str) -> None:
    """Push a result to Telegram, if it's configured."""
    if not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_ALLOWED_IDS):
        return
    from .channels import telegram

    for chat_id in config.TELEGRAM_ALLOWED_IDS:
        try:
            telegram._send(chat_id, text)
        except Exception as exc:
            print(f"[jarvis] could not notify {chat_id}: {exc!r}")


def run_job(job: dict, notify: bool = True) -> str:
    """Run one job and return what Jarvis said."""
    name = job["name"]
    print(f"[jarvis] running job: {name}")
    reply, _ = brain.think(job["prompt"].strip())

    target = job.get("file")
    if target:
        memory.append(
            target.format(date=memory.today()),
            f"\n## {name} - {memory.timestamp()}\n\n{reply}\n",
        )
    if notify and job.get("notify", True):
        _notify(f"[{name}]\n\n{reply}")
    _record(name, _dt.datetime.now())
    return reply


def run_named(name: str) -> int:
    """Run a single job by name, right now, ignoring the schedule."""
    matches = [j for j in load_jobs() if j["name"].lower() == name.lower()]
    if not matches:
        available = ", ".join(j["name"] for j in load_jobs()) or "(none defined)"
        print(f"No job called {name!r}. Available: {available}")
        return 1
    print(run_job(matches[0]))
    return 0


def run() -> int:
    config.ensure_dirs()
    jobs = load_jobs()
    if not jobs:
        print(f"No jobs defined in {JOBS_FILE}.")
        return 1

    print(f"[jarvis] scheduler up with {len(jobs)} job(s):")
    for job in jobs:
        print(f"  {job['at']:>5}  {','.join(job.get('days', ['daily'])):<27} {job['name']}")
    print("[jarvis] Ctrl-C to stop.")

    while True:
        try:
            now = _dt.datetime.now()
            for job in load_jobs():  # reread each tick so edits apply live
                if due(job, now):
                    try:
                        run_job(job)
                    except Exception as exc:
                        print(f"[jarvis] job {job['name']!r} failed: {exc!r}")
                        _record(job["name"], now)  # don't retry-loop a broken job
            time.sleep(TICK_SECONDS)
        except KeyboardInterrupt:
            print("\n[jarvis] scheduler stopped.")
            return 0


if __name__ == "__main__":
    raise SystemExit(run())
