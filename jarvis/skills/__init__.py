"""Tool registry.

Adding a capability to Jarvis is: write a module here that exposes a ``TOOLS``
list of ``@beta_tool`` functions, then import it below. Nothing else changes.
"""

from . import calendar, content, email, notes, schedule, trading

# Anthropic-hosted search. Runs on Anthropic's servers, so there is no function
# to implement - it just needs declaring.
WEB_SEARCH = {"type": "web_search_20260209", "name": "web_search", "max_uses": 8}

TOOLS = [
    *notes.TOOLS,
    *schedule.TOOLS,
    *calendar.TOOLS,
    *content.TOOLS,
    *email.TOOLS,
    *trading.TOOLS,
    WEB_SEARCH,
]
