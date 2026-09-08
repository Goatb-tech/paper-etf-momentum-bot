from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .alerts import notify
from .alpaca import AlpacaPaperClient
from .config import Settings
from .models import Signal
from .risk import DailyLossStop, build_position_plan
from .strategy import ranked_signals


NEW_YORK = ZoneInfo("America/New_York")


def run_rebalance(settings: Settings, force: bool = False) -> int:
    """Create at most one paper bracket order per eligible ETF on weekly rebalance day.

    The runner never changes broker endpoints and uses only complete prior-day bars for signals.
    """
    now = datetime.now(NEW_YORK)
    client = AlpacaPaperClient(settings.api_key, settings.api_secret, settings.data_feed)
    clock = client.get_clock()
    if not clock.get("is_open"):
        notify(settings.alert_webhook_url, "PAPER ETF BOT: market closed; no orders submitted.")
        return 0
    if now.weekday() != 1 and not force:  # Tuesday, avoiding unnecessary daily turnover.
        notify(settings.alert_webhook_url, "PAPER ETF BOT: not Tuesday rebalance window; no orders submitted.")
        return 0

    account = client.get_account()
    equity = float(account["equity"])
    cash = float(account["cash"])
    opening_equity = float(account.get("last_equity") or equity)
    if DailyLossStop(settings.state_path, settings.daily_loss_limit).breached(equity, now.date(), opening_equity):
        notify(
            settings.alert_webhook_url,
            f"PAPER ETF BOT HALTED: daily equity loss reached {settings.daily_loss_limit:.2%}; new entries blocked.",
        )
        return 0

    history = client.daily_bars(settings.universe, now.date() - timedelta(days=440), now.date())
    # Alpaca may return the currently forming daily bar during market hours. It must never be a strategy input.
    completed_history = {
        symbol: [bar for bar in bars if bar.date < now.date()]
        for symbol, bars in history.items()
    }
    signals = ranked_signals(
        completed_history,
        settings.stop_atr_multiple,
        settings.reward_to_risk,
        settings.max_positions,
    )
    positions = {item["symbol"] for item in client.list_positions()}
    open_symbols = {item["symbol"] for item in client.list_open_orders()}
    submitted = 0
    remaining_slots = max(settings.max_positions - len(positions), 0)
    available_cash = cash

    for signal in signals:
        if remaining_slots == 0:
            break
        if signal.symbol in positions or signal.symbol in open_symbols:
            continue
        quote = client.latest_quote(signal.symbol)
        entry = float(quote.get("ap") or quote.get("bp") or signal.close)
        stop = round(entry - signal.atr * settings.stop_atr_multiple, 2)
        target = round(entry + (entry - stop) * settings.reward_to_risk, 2)
        live_price_signal = Signal(signal.symbol, signal.score, entry, signal.atr, stop, target)
        plan = build_position_plan(
            live_price_signal,
            equity,
            available_cash,
            settings.risk_per_trade,
            settings.max_position_allocation,
        )
        if plan is None:
            notify(settings.alert_webhook_url, f"PAPER ETF BOT: skipped {signal.symbol}; position rounds to zero.")
            continue
        client_order_id = f"etf-momentum-{now:%Y%m%d}-{plan.symbol}".lower()
        order = client.submit_bracket_buy(plan, client_order_id)
        submitted += 1
        remaining_slots -= 1
        available_cash -= plan.qty * plan.entry
        notify(
            settings.alert_webhook_url,
            "PAPER ETF BOT ORDER: "
            f"{plan.symbol} qty={plan.qty} estimate={plan.entry:.2f} stop={plan.stop:.2f} "
            f"target={plan.target:.2f} risk=${plan.risk_dollars:.2f} id={order.get('id', 'unknown')}",
        )

    if submitted == 0:
        notify(settings.alert_webhook_url, "PAPER ETF BOT: no eligible new entries.")
    return submitted
