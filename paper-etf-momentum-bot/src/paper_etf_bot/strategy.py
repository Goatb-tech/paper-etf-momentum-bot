from __future__ import annotations

from collections.abc import Mapping, Sequence
from statistics import fmean

from .models import Bar, Signal


LOOKBACK = 200


def average_true_range(bars: Sequence[Bar], periods: int = 20) -> float:
    if len(bars) < periods + 1:
        raise ValueError(f"Need at least {periods + 1} bars to calculate ATR.")
    true_ranges = []
    for previous, current in zip(bars[-periods - 1 : -1], bars[-periods:]):
        true_ranges.append(max(current.high - current.low, abs(current.high - previous.close), abs(current.low - previous.close)))
    return fmean(true_ranges)


def signal_for(symbol: str, bars: Sequence[Bar], stop_atr_multiple: float, reward_to_risk: float) -> Signal | None:
    """Return a signal based only on the supplied, completed daily bars."""
    if len(bars) < LOOKBACK:
        return None
    closes = [bar.close for bar in bars]
    close = closes[-1]
    sma_200 = fmean(closes[-LOOKBACK:])
    return_63 = close / closes[-64] - 1
    return_126 = close / closes[-127] - 1
    if close <= sma_200 or return_63 <= 0 or return_126 <= 0:
        return None
    atr = average_true_range(bars)
    stop = round(close - (atr * stop_atr_multiple), 2)
    if stop <= 0 or stop >= close:
        return None
    target = round(close + ((close - stop) * reward_to_risk), 2)
    # Favor both intermediate momentum horizons; not a prediction of future returns.
    return Signal(symbol=symbol, score=return_63 + return_126, close=close, atr=atr, stop=stop, target=target)


def ranked_signals(
    history: Mapping[str, Sequence[Bar]],
    stop_atr_multiple: float,
    reward_to_risk: float,
    limit: int,
) -> list[Signal]:
    signals = [
        signal
        for symbol, bars in history.items()
        if (signal := signal_for(symbol, bars, stop_atr_multiple, reward_to_risk)) is not None
    ]
    return sorted(signals, key=lambda item: item.score, reverse=True)[:limit]
