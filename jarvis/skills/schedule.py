"""Daily planning - the day's plan lives in vault/daily/YYYY-MM-DD.md."""

from anthropic import beta_tool

from .. import memory


@beta_tool
def get_day_plan(date: str = "") -> str:
    """Read the plan for a given day.

    Args:
        date: ISO date like "2026-09-09". Defaults to today.
    """
    day = date or memory.today()
    content = memory.read(f"daily/{day}.md")
    return content or f"(no plan written for {day} yet)"


@beta_tool
def set_day_plan(plan: str, date: str = "") -> str:
    """Replace the plan for a day. Write it as a markdown schedule with times,
    and keep deep-work blocks unbroken rather than scattering small tasks.

    Args:
        plan: The full markdown plan for the day.
        date: ISO date. Defaults to today.
    """
    day = date or memory.today()
    memory.write(f"daily/{day}.md", f"# {day}\n\n{plan.strip()}\n")
    return f"plan set for {day}"


@beta_tool
def add_task(task: str, date: str = "") -> str:
    """Add a single task to a day's plan without rewriting the rest of it.

    Args:
        task: The task, phrased as one concrete action.
        date: ISO date. Defaults to today.
    """
    day = date or memory.today()
    memory.append(f"daily/{day}.md", f"- [ ] {task}")
    return f"added to {day}: {task}"


@beta_tool
def log_note(entry: str) -> str:
    """Capture a passing thought, decision or something the user told you into
    today's log so it isn't lost. Use this liberally.

    Args:
        entry: What to record, in one or two sentences.
    """
    memory.append("inbox/log.md", f"- {memory.timestamp()} - {entry}")
    return "logged"


TOOLS = [get_day_plan, set_day_plan, add_task, log_note]
