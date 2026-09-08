from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import PAPER_TRADING_URL
from .models import Bar, PositionPlan


DATA_URL = "https://data.alpaca.markets"


class AlpacaApiError(RuntimeError):
    pass


class AlpacaPaperClient:
    """Minimal REST client whose trading URL is permanently fixed to Alpaca paper trading."""

    def __init__(self, api_key: str, api_secret: str, data_feed: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.data_feed = data_feed

    def get_account(self) -> dict[str, Any]:
        return self._request(PAPER_TRADING_URL, "/v2/account")

    def get_clock(self) -> dict[str, Any]:
        return self._request(PAPER_TRADING_URL, "/v2/clock")

    def list_positions(self) -> list[dict[str, Any]]:
        return self._request(PAPER_TRADING_URL, "/v2/positions")

    def list_open_orders(self) -> list[dict[str, Any]]:
        return self._request(PAPER_TRADING_URL, "/v2/orders", {"status": "open", "nested": "true", "limit": 500})

    def latest_quote(self, symbol: str) -> dict[str, Any]:
        payload = self._request(DATA_URL, f"/v2/stocks/{symbol}/quotes/latest", {"feed": self.data_feed})
        return payload["quote"]

    def daily_bars(self, symbols: Iterable[str], start: date, end: date) -> dict[str, list[Bar]]:
        payload = self._request(
            DATA_URL,
            "/v2/stocks/bars",
            {
                "symbols": ",".join(symbols),
                "timeframe": "1Day",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "adjustment": "all",
                "feed": self.data_feed,
            },
        )
        return {
            symbol: [
                Bar(
                    date=datetime.fromisoformat(item["t"].replace("Z", "+00:00")).date(),
                    open=float(item["o"]),
                    high=float(item["h"]),
                    low=float(item["l"]),
                    close=float(item["c"]),
                    volume=float(item.get("v", 0)),
                )
                for item in rows
            ]
            for symbol, rows in payload.get("bars", {}).items()
        }

    def submit_bracket_buy(self, plan: PositionPlan, client_order_id: str) -> dict[str, Any]:
        if plan.qty < 1 or plan.stop >= plan.entry or plan.target <= plan.entry:
            raise ValueError("Invalid bracket order plan.")
        return self._request(
            PAPER_TRADING_URL,
            "/v2/orders",
            method="POST",
            body={
                "symbol": plan.symbol,
                "qty": str(plan.qty),
                "side": "buy",
                "type": "market",
                "time_in_force": "gtc",
                "order_class": "bracket",
                "client_order_id": client_order_id,
                "take_profit": {"limit_price": f"{plan.target:.2f}"},
                "stop_loss": {"stop_price": f"{plan.stop:.2f}"},
            },
        )

    def _request(
        self,
        base_url: str,
        path: str,
        query: dict[str, str | int] | None = None,
        method: str = "GET",
        body: dict[str, Any] | None = None,
    ) -> Any:
        if base_url == PAPER_TRADING_URL and not base_url.startswith("https://paper-api.alpaca.markets"):
            raise AlpacaApiError("Live-trading endpoints are prohibited.")
        url = f"{base_url}{path}"
        if query:
            url += "?" + urlencode(query)
        request = Request(
            url,
            data=json.dumps(body).encode() if body else None,
            method=method,
            headers={
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.api_secret,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "paper-etf-bot/0.1",
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode())
        except HTTPError as error:
            detail = error.read().decode(errors="replace")
            request_id = error.headers.get("X-Request-ID", "unknown")
            raise AlpacaApiError(f"Alpaca HTTP {error.code}: {detail} (request id: {request_id})") from error
        except URLError as error:
            raise AlpacaApiError(f"Cannot reach Alpaca: {error.reason}") from error

