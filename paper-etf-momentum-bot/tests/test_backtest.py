import unittest
from datetime import date, timedelta

from paper_etf_bot.backtest import backtest
from paper_etf_bot.models import Bar


def bars(symbol_offset: float) -> list[Bar]:
    first = date(2020, 1, 1)
    result = []
    for index in range(280):
        close = 100 + symbol_offset + index * 0.25
        result.append(Bar(first + timedelta(days=index), close - 0.1, close + 1, close - 1, close))
    return result


class BacktestTests(unittest.TestCase):
    def test_backtest_returns_comparison_metrics(self) -> None:
        result = backtest({"SPY": bars(0), "QQQ": bars(5)}, max_positions=1)
        self.assertGreater(result.ending_equity, 0)
        self.assertGreater(result.trades, 0)
        self.assertLessEqual(result.max_drawdown, 0)
