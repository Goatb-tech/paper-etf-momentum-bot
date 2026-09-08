from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PAPER_TRADING_URL = "https://paper-api.alpaca.markets"
DEFAULT_UNIVERSE = (
    "SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY",
    "XLP", "XLU", "XLB", "XLRE", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC",
)


def _decimal(name: str, default: str) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError as error:
        raise ValueError(f"{name} must be a decimal number") from error


def _integer(name: str, default: str) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error


@dataclass(frozen=True)
class Settings:
    api_key: str
    api_secret: str
    data_feed: str
    risk_per_trade: float
    hard_risk_cap: float
    daily_loss_limit: float
    max_positions: int
    max_position_allocation: float
    stop_atr_multiple: float
    reward_to_risk: float
    alert_webhook_url: str | None
    state_path: Path
    universe: tuple[str, ...] = DEFAULT_UNIVERSE

    @classmethod
    def from_env(cls, require_credentials: bool = True) -> "Settings":
        # Intentionally do not allow configuration of a live trading host.
        endpoint = os.getenv("ALPACA_TRADING_BASE_URL", PAPER_TRADING_URL).rstrip("/")
        if endpoint != PAPER_TRADING_URL:
            raise ValueError(
                "This application is paper-only. ALPACA_TRADING_BASE_URL must be "
                f"{PAPER_TRADING_URL}."
            )
        api_key = os.getenv("ALPACA_API_KEY", "")
        api_secret = os.getenv("ALPACA_API_SECRET", "")
        if require_credentials and (not api_key or not api_secret):
            raise ValueError("Set ALPACA_API_KEY and ALPACA_API_SECRET in .env before running.")
        settings = cls(
            api_key=api_key,
            api_secret=api_secret,
            data_feed=os.getenv("ALPACA_DATA_FEED", "sip").lower(),
            risk_per_trade=_decimal("BOT_RISK_PER_TRADE", "0.0025"),
            hard_risk_cap=_decimal("BOT_HARD_RISK_CAP", "0.005"),
            daily_loss_limit=_decimal("BOT_DAILY_LOSS_LIMIT", "0.01"),
            max_positions=_integer("BOT_MAX_POSITIONS", "4"),
            max_position_allocation=_decimal("BOT_MAX_POSITION_ALLOCATION", "0.25"),
            stop_atr_multiple=_decimal("BOT_STOP_ATR_MULTIPLE", "2.0"),
            reward_to_risk=_decimal("BOT_REWARD_TO_RISK", "3.0"),
            alert_webhook_url=os.getenv("BOT_ALERT_WEBHOOK_URL") or None,
            state_path=Path(os.getenv("BOT_STATE_PATH", "data/state.json")),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.data_feed not in {"sip", "iex", "delayed_sip"}:
            raise ValueError("ALPACA_DATA_FEED must be sip, iex, or delayed_sip.")
        if not 0 < self.risk_per_trade <= self.hard_risk_cap <= 0.005:
            raise ValueError("Risk per trade must be positive and cannot exceed the 0.5% hard cap.")
        if not 0 < self.daily_loss_limit <= 0.01:
            raise ValueError("Daily loss limit must be positive and cannot exceed 1%.")
        if not 1 <= self.max_positions <= 10:
            raise ValueError("BOT_MAX_POSITIONS must be between 1 and 10.")
        if not 0 < self.max_position_allocation <= 0.25:
            raise ValueError("BOT_MAX_POSITION_ALLOCATION cannot exceed 25%.")
        if self.stop_atr_multiple <= 0 or self.reward_to_risk < 2:
            raise ValueError("Stop ATR multiple must be positive and reward-to-risk must be at least 2.")
