from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path

from .models import Bar


CSV_FIELDS = ("date", "open", "high", "low", "close", "volume")


def save_history(history: Mapping[str, Sequence[Bar]], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for symbol, bars in history.items():
        with (directory / f"{symbol}.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(
                {
                    "date": item.date.isoformat(),
                    "open": item.open,
                    "high": item.high,
                    "low": item.low,
                    "close": item.close,
                    "volume": item.volume,
                }
                for item in bars
            )


def load_history(directory: Path) -> dict[str, list[Bar]]:
    history: dict[str, list[Bar]] = {}
    for path in sorted(directory.glob("*.csv")):
        with path.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        history[path.stem] = [
            Bar(
                date=date.fromisoformat(row["date"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row.get("volume") or 0),
            )
            for row in rows
        ]
    if not history:
        raise ValueError(f"No CSV history files found in {directory}.")
    return history

