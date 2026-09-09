"""Market analysis and a trade journal.

Jarvis reads the market and writes up ideas. It does not place orders: order
routing is stubbed behind a gate on purpose. An LLM loop with live broker
credentials is a genuinely bad idea until you have months of logged, reviewed
signals to judge it on.
"""

from anthropic import beta_tool

from .. import config, memory

JOURNAL = "trading/journal.md"


def _yfinance():
    try:
        import yfinance  # noqa: PLC0415 - optional dependency, imported on demand
    except ImportError:
        return None
    return yfinance


@beta_tool
def get_quote(symbol: str) -> str:
    """Get the latest price and recent range for a ticker.

    Args:
        symbol: Ticker, e.g. "SPY", "NVDA", "BTC-USD".
    """
    yf = _yfinance()
    if yf is None:
        return "yfinance is not installed - run: pip install yfinance"
    try:
        history = yf.Ticker(symbol).history(period="1mo", interval="1d")
    except Exception as exc:  # network/ticker errors surface as tool output
        return f"could not fetch {symbol}: {exc}"
    if history.empty:
        return f"no data for {symbol} - check the ticker"

    last = history["Close"].iloc[-1]
    prev = history["Close"].iloc[-2] if len(history) > 1 else last
    change = (last - prev) / prev * 100 if prev else 0.0
    return (
        f"{symbol}: {last:.2f} ({change:+.2f}% on the day)\n"
        f"1-month range: {history['Low'].min():.2f} - {history['High'].max():.2f}\n"
        f"20d average close: {history['Close'].tail(20).mean():.2f}\n"
        f"last session volume: {int(history['Volume'].iloc[-1]):,}"
    )


@beta_tool
def get_price_history(symbol: str, period: str = "6mo", interval: str = "1d") -> str:
    """Get summary statistics over a longer window, for trend and volatility
    context. Returns statistics rather than every bar, to stay readable.

    Args:
        symbol: Ticker, e.g. "SPY".
        period: Window such as "1mo", "6mo", "1y", "5y".
        interval: Bar size such as "1d", "1h", "1wk".
    """
    yf = _yfinance()
    if yf is None:
        return "yfinance is not installed - run: pip install yfinance"
    try:
        history = yf.Ticker(symbol).history(period=period, interval=interval)
    except Exception as exc:
        return f"could not fetch {symbol}: {exc}"
    if history.empty:
        return f"no data for {symbol} over {period}"

    closes = history["Close"]
    returns = closes.pct_change().dropna()
    annualised_vol = returns.std() * (252 ** 0.5) * 100
    total_return = (closes.iloc[-1] / closes.iloc[0] - 1) * 100
    return (
        f"{symbol} over {period} ({interval} bars, {len(closes)} points)\n"
        f"first {closes.iloc[0]:.2f} -> last {closes.iloc[-1]:.2f} ({total_return:+.1f}%)\n"
        f"high {history['High'].max():.2f} / low {history['Low'].min():.2f}\n"
        f"annualised volatility: {annualised_vol:.1f}%\n"
        f"50-bar avg: {closes.tail(50).mean():.2f} | 200-bar avg: {closes.tail(200).mean():.2f}"
    )


@beta_tool
def log_trade_idea(
    symbol: str,
    direction: str,
    thesis: str,
    entry: str = "",
    stop: str = "",
    target: str = "",
) -> str:
    """Record a trade idea in the journal so it can be reviewed later against
    what actually happened. Always log the thesis, not just the levels.

    Args:
        symbol: Ticker.
        direction: "long", "short", or the structure, e.g. "put credit spread".
        thesis: Why this trade, in a few sentences, including what would
            invalidate it.
        entry: Intended entry level or zone.
        stop: Invalidation level.
        target: Objective.
    """
    memory.append(
        JOURNAL,
        f"\n## {memory.timestamp()} - {symbol.upper()} {direction}\n"
        f"- entry: {entry or 'n/a'}\n- stop: {stop or 'n/a'}\n"
        f"- target: {target or 'n/a'}\n- thesis: {thesis}\n- outcome: _pending_\n",
    )
    return f"logged {symbol.upper()} {direction} to the journal - no order was placed"


@beta_tool
def read_journal() -> str:
    """Read the trade journal, including past ideas and their outcomes. Read
    this before proposing a new trade so you don't repeat a losing pattern."""
    return memory.read(JOURNAL) or "(journal is empty)"


@beta_tool
def place_order(symbol: str, side: str, quantity: float) -> str:
    """Place a real broker order. Intentionally not wired to a broker.

    Args:
        symbol: Ticker.
        side: "buy" or "sell".
        quantity: Number of shares or contracts.
    """
    if not config.ALLOW_LIVE_TRADES:
        return (
            f"ORDER BLOCKED - no order was placed for {side} {quantity} {symbol}. "
            "Live trading is off and no broker is connected. Log the idea with "
            "log_trade_idea and tell the user to place it themselves."
        )
    return (
        "Live trading is enabled in config, but no broker adapter is implemented. "
        "Wire up your broker's SDK in jarvis/skills/trading.py before relying on this."
    )


TOOLS = [get_quote, get_price_history, log_trade_idea, read_journal, place_order]
