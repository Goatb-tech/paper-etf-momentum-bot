from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean, stdev
from collections.abc import Mapping, Sequence

from .models import Bar
from .strategy import ranked_signals


@dataclass(frozen=True)
class BacktestResult:
    starting_equity: float
    ending_equity: float
    cagr: float
    max_drawdown: float
    annualized_volatility: float
    sharpe: float
    trades: int
    benchmark_cagr: float
    benchmark_max_drawdown: float


@dataclass
class _Position:
    qty: int
    stop: float
    target: float


def _drawdown(values: Sequence[float]) -> float:
    peak = values[0]
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        worst = min(worst, value / peak - 1)
    return worst


def _cagr(values: Sequence[float]) -> float:
    years = max((len(values) - 1) / 252, 1 / 252)
    return (values[-1] / values[0]) ** (1 / years) - 1


def backtest(
    history: Mapping[str, Sequence[Bar]],
    benchmark: str = "SPY",
    starting_equity: float = 100_000,
    max_positions: int = 4,
    stop_atr_multiple: float = 2.0,
    reward_to_risk: float = 3.0,
    trading_cost_bps: float = 5.0,
) -> BacktestResult:
    """Daily-bar simulation: signals use yesterday's close, fills use today's open.

    This is deliberately simple and is a screening tool, not evidence of a tradable edge.
    """
    if benchmark not in history:
        raise ValueError(f"Benchmark {benchmark} is missing from the downloaded history.")
    by_symbol = {symbol: {bar.date: bar for bar in bars} for symbol, bars in history.items()}
    dates = sorted(set.intersection(*(set(rows) for rows in by_symbol.values())))
    if len(dates) <= 201:
        raise ValueError("Need at least 202 common daily bars for a backtest.")
    fee = trading_cost_bps / 10_000
    cash = starting_equity
    positions: dict[str, _Position] = {}
    equity_curve = [starting_equity]
    benchmark_curve = [starting_equity]
    trades = 0

    for index in range(201, len(dates)):
        current_date = dates[index]
        previous_dates = dates[:index]
        # All inputs end at yesterday, preventing same-day close look-ahead.
        windowed = {symbol: [by_symbol[symbol][item] for item in previous_dates] for symbol in history}
        targets = {
            signal.symbol: signal
            for signal in ranked_signals(windowed, stop_atr_multiple, reward_to_risk, max_positions)
        }

        # First, process GTC bracket exits using intraday high/low. A gap through a stop fills at the open.
        for symbol, position in list(positions.items()):
            bar = by_symbol[symbol][current_date]
            if bar.low <= position.stop:
                fill = min(bar.open, position.stop)
            elif bar.high >= position.target:
                fill = max(bar.open, position.target)
            elif symbol not in targets:
                fill = bar.open
            else:
                continue
            cash += position.qty * fill * (1 - fee)
            del positions[symbol]
            trades += 1

        current_equity = cash + sum(position.qty * by_symbol[symbol][current_date].open for symbol, position in positions.items())
        allocation = current_equity / max_positions
        for symbol, signal in targets.items():
            if symbol in positions:
                continue
            bar = by_symbol[symbol][current_date]
            qty = math.floor(min(allocation, cash) / (bar.open * (1 + fee)))
            if qty < 1:
                continue
            cash -= qty * bar.open * (1 + fee)
            risk_per_share = signal.close - signal.stop
            # Stops and targets are formed from yesterday's completed data and are never revised intra-day.
            positions[symbol] = _Position(qty=qty, stop=signal.stop, target=signal.target)
            trades += 1

        equity_curve.append(cash + sum(position.qty * by_symbol[symbol][current_date].close for symbol, position in positions.items()))
        first_benchmark_close = by_symbol[benchmark][dates[200]].close
        benchmark_curve.append(starting_equity * by_symbol[benchmark][current_date].close / first_benchmark_close)

    daily_returns = [equity_curve[i] / equity_curve[i - 1] - 1 for i in range(1, len(equity_curve))]
    volatility = stdev(daily_returns) * math.sqrt(252) if len(daily_returns) > 1 else 0.0
    sharpe = (fmean(daily_returns) / stdev(daily_returns) * math.sqrt(252)) if len(daily_returns) > 1 and stdev(daily_returns) else 0.0
    return BacktestResult(
        starting_equity=starting_equity,
        ending_equity=equity_curve[-1],
        cagr=_cagr(equity_curve),
        max_drawdown=_drawdown(equity_curve),
        annualized_volatility=volatility,
        sharpe=sharpe,
        trades=trades,
        benchmark_cagr=_cagr(benchmark_curve),
        benchmark_max_drawdown=_drawdown(benchmark_curve),
    )
