import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from paper_etf_bot.models import Bar
from paper_etf_bot.risk import DailyLossStop, build_position_plan
from paper_etf_bot.strategy import ranked_signals, signal_for


def rising_bars(count: int = 230) -> list[Bar]:
    start = date(2024, 1, 1)
    return [
        Bar(start + timedelta(days=index), 100 + index, 101 + index, 99 + index, 100 + index)
        for index in range(count)
    ]


class StrategyAndRiskTests(unittest.TestCase):
    def test_rising_series_produces_valid_signal(self) -> None:
        signal = signal_for("SPY", rising_bars(), 2.0, 3.0)
        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertGreater(signal.target, signal.close)
        self.assertLess(signal.stop, signal.close)

    def test_rankings_limit_count(self) -> None:
        history = {"SPY": rising_bars(), "QQQ": rising_bars(), "IWM": rising_bars()}
        self.assertEqual(len(ranked_signals(history, 2.0, 3.0, 2)), 2)

    def test_position_size_honors_risk_and_allocation(self) -> None:
        signal = signal_for("SPY", rising_bars(), 2.0, 3.0)
        assert signal is not None
        plan = build_position_plan(signal, equity=100_000, cash=100_000, risk_per_trade=0.0025, max_allocation=0.25)
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertLessEqual(plan.risk_dollars, 250.01)
        self.assertLessEqual(plan.qty * plan.entry, 25_000.01)

    def test_daily_loss_stop_persists_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stop = DailyLossStop(Path(directory) / "state.json", 0.01)
            today = date(2026, 9, 5)
            self.assertFalse(stop.breached(100_000, today))
            self.assertTrue(stop.breached(99_000, today))
            self.assertTrue(stop.breached(100_000, today), "The daily halt must remain sticky until the next date.")
