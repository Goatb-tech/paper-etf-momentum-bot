from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path

from .alpaca import AlpacaPaperClient
from .backtest import backtest
from .config import Settings
from .data import load_history, save_history
from .runner import run_rebalance


def load_env_file(path: Path = Path(".env")) -> None:
    """Small dependency-free .env reader. Existing environment variables win."""
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _result_text(result: object) -> str:
    fields = (
        "starting_equity", "ending_equity", "cagr", "max_drawdown", "annualized_volatility",
        "sharpe", "trades", "benchmark_cagr", "benchmark_max_drawdown",
    )
    lines = ["BACKTEST RESULT"]
    for field in fields:
        value = getattr(result, field)
        if field in {"cagr", "max_drawdown", "annualized_volatility", "benchmark_cagr", "benchmark_max_drawdown"}:
            lines.append(f"{field}: {value:.2%}")
        elif isinstance(value, float):
            lines.append(f"{field}: {value:,.2f}")
        else:
            lines.append(f"{field}: {value}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Paper-only ETF trend/momentum bot")
    subparsers = parser.add_subparsers(dest="command", required=True)
    download = subparsers.add_parser("download", help="Download adjusted daily ETF bars from Alpaca.")
    download.add_argument("--start", default="2016-01-01")
    download.add_argument("--end", default=date.today().isoformat())
    download.add_argument("--output", default="data/history")
    test = subparsers.add_parser("backtest", help="Backtest CSV bars against SPY buy-and-hold.")
    test.add_argument("--history", default="data/history")
    test.add_argument("--benchmark", default="SPY")
    test.add_argument("--capital", type=float, default=100_000)
    test.add_argument("--cost-bps", type=float, default=5.0)
    test.add_argument("--start", help="Optional inclusive ISO date for an in-sample or out-of-sample window.")
    test.add_argument("--end", help="Optional inclusive ISO date for an in-sample or out-of-sample window.")
    execute = subparsers.add_parser("run", help="Run one paper-only weekly rebalance check.")
    execute.add_argument("--force", action="store_true", help="Allow a manual run on a non-Tuesday market session.")
    args = parser.parse_args()
    load_env_file()

    if args.command == "download":
        settings = Settings.from_env()
        client = AlpacaPaperClient(settings.api_key, settings.api_secret, settings.data_feed)
        history = client.daily_bars(settings.universe, date.fromisoformat(args.start), date.fromisoformat(args.end))
        save_history(history, Path(args.output))
        print(f"Saved {sum(len(rows) for rows in history.values())} daily bars for {len(history)} symbols to {args.output}.")
    elif args.command == "backtest":
        history = load_history(Path(args.history))
        start = date.fromisoformat(args.start) if args.start else None
        end = date.fromisoformat(args.end) if args.end else None
        if start or end:
            history = {
                symbol: [bar for bar in bars if (start is None or bar.date >= start) and (end is None or bar.date <= end)]
                for symbol, bars in history.items()
            }
        result = backtest(history, benchmark=args.benchmark, starting_equity=args.capital, trading_cost_bps=args.cost_bps)
        print(_result_text(result))
    elif args.command == "run":
        settings = Settings.from_env()
        count = run_rebalance(settings, force=args.force)
        print(f"Submitted {count} paper parent order(s).")


if __name__ == "__main__":
    main()
