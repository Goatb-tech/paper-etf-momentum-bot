from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Bar:
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class Signal:
    symbol: str
    score: float
    close: float
    atr: float
    stop: float
    target: float


@dataclass(frozen=True)
class PositionPlan:
    symbol: str
    qty: int
    entry: float
    stop: float
    target: float
    risk_dollars: float

