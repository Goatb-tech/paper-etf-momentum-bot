import os
import unittest
from unittest.mock import patch

from paper_etf_bot.config import PAPER_TRADING_URL, Settings


class SettingsTests(unittest.TestCase):
    def test_defaults_are_paper_only_and_within_risk_caps(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_env(require_credentials=False)
        self.assertEqual(settings.risk_per_trade, 0.0025)
        self.assertEqual(settings.hard_risk_cap, 0.005)
        self.assertEqual(settings.daily_loss_limit, 0.01)

    def test_live_endpoint_is_rejected(self) -> None:
        with patch.dict(os.environ, {"ALPACA_TRADING_BASE_URL": "https://api.alpaca.markets"}, clear=True):
            with self.assertRaisesRegex(ValueError, "paper-only"):
                Settings.from_env(require_credentials=False)

    def test_over_cap_risk_is_rejected(self) -> None:
        with patch.dict(os.environ, {"BOT_RISK_PER_TRADE": "0.006"}, clear=True):
            with self.assertRaisesRegex(ValueError, "0.5%"):
                Settings.from_env(require_credentials=False)

