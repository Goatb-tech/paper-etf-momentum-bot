from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

from .models import PositionPlan, Signal


class DailyLossStop:
    """Persists a daily equity baseline and blocks new entries after the loss limit."""

    def __init__(self, path: Path, loss_limit: float) -> None:
        self.path = path
        self.loss_limit = loss_limit

    def breached(self, equity: float, today: date, opening_equity: float | None = None) -> bool:
        state = self._read()
        if state.get("date") != today.isoformat():
            starting_equity = opening_equity if opening_equity is not None else equity
            halted = equity <= starting_equity * (1 - self.loss_limit)
            self._write({"date": today.isoformat(), "starting_equity": starting_equity, "halted": halted})
            return halted
        if state.get("halted"):
            return True
        starting_equity = float(state["starting_equity"])
        halted = equity <= starting_equity * (1 - self.loss_limit)
        if halted:
            state["halted"] = True
            self._write(state)
        return halted

    def _read(self) -> dict[str, object]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def _write(self, state: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state, indent=2) + "\n")


def build_position_plan(
    signal: Signal,
    equity: float,
    cash: float,
    risk_per_trade: float,
    max_allocation: float,
) -> PositionPlan | None:
    risk_per_share = signal.close - signal.stop
    if risk_per_share <= 0:
        return None
    risk_budget = equity * risk_per_trade
    qty_by_risk = math.floor(risk_budget / risk_per_share)
    qty_by_cash = math.floor(min(cash, equity * max_allocation) / signal.close)
    qty = min(qty_by_risk, qty_by_cash)
    if qty < 1:
        return None
    return PositionPlan(
        symbol=signal.symbol,
        qty=qty,
        entry=signal.close,
        stop=signal.stop,
        target=signal.target,
        risk_dollars=round(qty * risk_per_share, 2),
    )
