# Paper-only ETF trend/momentum bot

This is a deliberately conservative first version of your system:

- US-listed, long-only ETFs; no leverage, shorts, options, or live orders.
- A simple daily trend/momentum ranking, designed for a multi-day-to-weeks holding period.
- Uses only completed daily bars: signals are calculated from yesterday's close and orders are created during the next regular session.
- New entries only on Tuesday at 09:45 America/New_York, avoiding daily turnover.
- Alpaca paper-trading bracket orders with a broker-held stop and profit target.
- Risk defaults: 0.25% of current paper equity per position, never over 0.5%; a 1% daily equity-loss threshold blocks all new entries.
- Optional Slack/Discord-style webhook alerts.

It is research software, not a profitable-trading claim or financial advice. Paper fills and historical backtests will differ from live markets. Do not change the hard safety limits to bypass the checks.

## Strategy being tested

Universe: `SPY QQQ IWM DIA XLK XLF XLE XLV XLI XLY XLP XLU XLB XLRE EFA EEM TLT IEF GLD DBC`.

At each Tuesday rebalance check, the strategy considers ETFs that meet all three rules using the preceding completed daily close:

1. Price is above its 200-day simple moving average.
2. Both 63- and 126-trading-day returns are positive.
3. The up-to-four strongest combined 63/126-day returns are eligible.

Each entry has an initial stop two 20-day ATRs below the current quote and target at 3R. The position-size calculation is `equity * 0.25% / (entry - stop)`, constrained by cash and a 25% maximum allocation. The baseline backtest includes a 5 basis-point cost on each fill and reports against SPY buy-and-hold.

This is a hypothesis to test, not an edge. Do not adjust parameters after seeing a result without recording the decision and retesting on untouched data.

The caps are **planned-risk** caps based on the expected fill and stop. Neither a stop order nor paper trading can make realized loss mathematically hard-capped: an ETF can gap through a stop, and a market entry can fill away from its last quote. The 1% daily stop therefore makes the system halt new entries for the rest of that day; it does not falsely promise to erase an already-open gap risk.

## Setup on your Mac

1. Create a paper-only Alpaca API key. Copy the example configuration, then fill in only those paper credentials:

   ```sh
   cp .env.example .env
   ```

2. Install the package in a virtual environment:

   ```sh
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -e .
   ```

3. Verify the safety and strategy tests:

   ```sh
   PYTHONPATH=src python3 -m unittest discover -s tests -v
   ```

4. Download adjusted daily data, then test the strategy:

   ```sh
   paper-etf-bot download --start 2016-01-01
   paper-etf-bot backtest --history data/history --capital 100000 --cost-bps 5
   ```

Use a `--capital` equal to your intended funding solely for comparable risk and sizing simulation. It does not connect or submit orders.

To make the intended out-of-sample check reproducible, choose the strategy rules before reviewing the later period. For example, use 2016 through 2023 for research, then run 2024 onward exactly once without changing rules:

```sh
paper-etf-bot backtest --start 2016-01-01 --end 2023-12-31
paper-etf-bot backtest --start 2024-01-01
```

## Paper runner

The production command is intentionally small and runs once:

```sh
paper-etf-bot run
```

Schedule it in your cloud provider for Tuesday at 09:45 America/New_York. Persist the `data/` directory because it contains the daily-loss baseline. Never schedule more than one instance at the same time. A Tuesday-only gate is also in code; `--force` is for a supervised manual paper test during an open market:

```sh
paper-etf-bot run --force
```

For a Docker-based scheduled job:

```sh
docker compose run --rm paper-etf-bot
```

Set `BOT_ALERT_WEBHOOK_URL` in your cloud secret manager (or `.env` locally) to receive skip, halt, and submitted-order notifications. Keep API keys and webhook URLs out of git, screenshots, and chat messages.

## Data requirement

Set `ALPACA_DATA_FEED=sip` only when your Alpaca plan permits real-time consolidated SIP data. Alpaca's Basic plan provides real-time IEX data, whereas its Algo Trader Plus plan provides all US stock exchanges; querying recent SIP data without the proper subscription can be rejected. See Alpaca's [market-data plan documentation](https://docs.alpaca.markets/us/docs/about-market-data-api) and [market-data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq).

The runner reads the current SIP quote for sizing but removes the forming current-day daily bar before evaluating a signal. This avoids intraday look-ahead in daily rules.

## Before allowing any real-money discussion

Run these gates in order:

1. Backtest from 2016 onward, then keep the most recent 20-30% as a completely untouched out-of-sample period.
2. Repeat it with higher costs (10-20 bps), different ETF universes, and excluded years. Record every result.
3. Paper trade for at least 8-12 weeks without parameter changes, comparing expected and actual fills.
4. Review maximum drawdown, turnover, missed fills, and failure alerts; only then decide whether more research is justified.

No version of this project should be pointed at a live trading endpoint without a separate, explicit design and review.
