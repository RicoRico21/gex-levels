"""Calendar, read through ICS feed URLs.

Every calendar app publishes a private ICS URL - Google calls it the "secret
address in iCal format", Apple and Outlook both have equivalents. Subscribing to
that URL gets us read access to the real calendar in about forty lines, with no
OAuth consent screen and no Google Cloud project. The tradeoff is that it is
read-only: Jarvis can plan around your meetings but cannot create them. That is
the right tradeoff for now - see SETUP.md if you want to add write access later.
"""

import datetime as _dt
import os
import threading

import requests
from anthropic import beta_tool

FEED_URLS = [u.strip() for u in os.getenv("JARVIS_CALENDAR_ICS_URLS", "").split(",") if u.strip()]
CACHE_SECONDS = 300
_cache: dict[str, tuple[float, str]] = {}
_lock = threading.Lock()


def _local_tz():
    return _dt.datetime.now().astimezone().tzinfo


def _fetch(url: str) -> str:
    """Fetch an ICS feed, cached briefly so a multi-tool turn doesn't refetch."""
    now = _dt.datetime.now().timestamp()
    with _lock:
        cached = _cache.get(url)
        if cached and now - cached[0] < CACHE_SECONDS:
            return cached[1]
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    text = response.text
    with _lock:
        _cache[url] = (now, text)
    return text


def _events(
    start: _dt.datetime, end: _dt.datetime
) -> list[tuple[_dt.datetime, _dt.datetime, str, bool]]:
    """All events across every feed in the window, sorted by start.

    Each entry is (start, end, title, all_day).
    """
    import icalendar
    import recurring_ical_events

    collected: list[tuple[_dt.datetime, _dt.datetime, str, bool]] = []
    for url in FEED_URLS:
        calendar = icalendar.Calendar.from_ical(_fetch(url))
        for event in recurring_ical_events.of(calendar).between(start, end):
            begins = event.get("DTSTART").dt
            ends = event.get("DTEND").dt if event.get("DTEND") else begins
            # All-day events come back as dates, not datetimes.
            all_day = not isinstance(begins, _dt.datetime)
            if not isinstance(begins, _dt.datetime):
                begins = _dt.datetime.combine(begins, _dt.time.min, tzinfo=_local_tz())
            if not isinstance(ends, _dt.datetime):
                ends = _dt.datetime.combine(ends, _dt.time.min, tzinfo=_local_tz())
            if begins.tzinfo is None:
                begins = begins.replace(tzinfo=_local_tz())
            if ends.tzinfo is None:
                ends = ends.replace(tzinfo=_local_tz())
            collected.append(
                (begins, ends, str(event.get("SUMMARY") or "(untitled)"), all_day)
            )
    return sorted(collected, key=lambda item: item[0])


@beta_tool
def get_calendar(days: int = 1) -> str:
    """Read the user's real calendar. Call this before planning their day or
    proposing a time for anything.

    Args:
        days: How many days ahead to look. 1 means today only.
    """
    if not FEED_URLS:
        return (
            "No calendar connected. The user can add one by putting their "
            "calendar's private ICS URL in JARVIS_CALENDAR_ICS_URLS in .env - "
            "SETUP.md step 6 has the instructions."
        )
    now = _dt.datetime.now(tz=_local_tz())
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        events = _events(start, start + _dt.timedelta(days=max(1, days)))
    except Exception as exc:
        return f"could not read the calendar: {exc}"
    if not events:
        return f"nothing on the calendar for the next {days} day(s)"

    lines, current_day = [], None
    for begins, ends, title, all_day in events:
        if begins.date() != current_day:
            current_day = begins.date()
            lines.append(f"\n{current_day:%A %d %b}")
        when = "all day     " if all_day else f"{begins:%H:%M}-{ends:%H:%M}"
        lines.append(f"  {when}  {title}")
    return "\n".join(lines).strip()


@beta_tool
def find_free_slots(
    date: str = "",
    min_minutes: int = 60,
    day_start: str = "09:00",
    day_end: str = "18:00",
) -> str:
    """Find gaps in the user's calendar big enough for focused work. Use this
    when scheduling deep work rather than guessing at free time.

    Args:
        date: ISO date like "2026-09-10". Defaults to today.
        min_minutes: Smallest gap worth reporting.
        day_start: Earliest time to consider, "HH:MM".
        day_end: Latest time to consider, "HH:MM".
    """
    if not FEED_URLS:
        return "No calendar connected - see SETUP.md step 6."
    tz = _local_tz()
    day = _dt.date.fromisoformat(date) if date else _dt.date.today()
    try:
        window_start = _dt.datetime.combine(day, _dt.time.fromisoformat(day_start), tzinfo=tz)
        window_end = _dt.datetime.combine(day, _dt.time.fromisoformat(day_end), tzinfo=tz)
    except ValueError as exc:
        return f"bad time format: {exc}"

    try:
        events = _events(window_start, window_end)
    except Exception as exc:
        return f"could not read the calendar: {exc}"

    free, cursor = [], window_start
    # All-day entries (birthdays, "offsite") shouldn't blank out the whole day.
    for begins, ends, _title, all_day in events:
        if all_day:
            continue
        if begins > cursor:
            gap = int((begins - cursor).total_seconds() // 60)
            if gap >= min_minutes:
                free.append(f"{cursor:%H:%M}-{begins:%H:%M} ({gap} min)")
        cursor = max(cursor, ends)
    if cursor < window_end:
        gap = int((window_end - cursor).total_seconds() // 60)
        if gap >= min_minutes:
            free.append(f"{cursor:%H:%M}-{window_end:%H:%M} ({gap} min)")

    if not free:
        return f"no free block of {min_minutes}+ min on {day:%A %d %b}"
    return f"free on {day:%A %d %b}:\n" + "\n".join(f"  {slot}" for slot in free)


TOOLS = [get_calendar, find_free_slots]
