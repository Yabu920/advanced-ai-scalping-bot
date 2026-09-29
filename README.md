# Advanced AI Scalping Bot

Stage 1 creates a clean, safe foundation for a future MT5-based AI scalping bot.

## Current Stage 1 Features

- Modular Python project structure
- Environment-based configuration
- MT5 terminal initialization and optional account login
- Market candle and tick data collection
- EMA, RSI, and ATR indicator calculations
- Basic market diagnostics snapshot
- Console and file logging
- Safe `main.py` diagnostics runner
- Basic pytest coverage for indicators

## Intentionally Not Included Yet

- Live trading
- Order execution
- AI or machine learning
- SMC logic
- Backtesting
- Telegram, dashboard, or alert integrations

## Installation

Create and activate a virtual environment, then install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Setup

Create a local `.env` file from the example:

```bash
cp .env.example .env
```

Fill in MT5 credentials only if you want the script to log in explicitly. If your MT5 terminal is already open and logged in, credentials can remain empty.

## Run Diagnostics

```bash
python main.py
```

The script connects to MT5, fetches candle data, calculates basic indicators, prints a market snapshot, and shuts down safely.

## Stage 2 Market Data Collection

Stage 2 adds multi-symbol and multi-timeframe market data collection. It collects clean OHLC candle data for configured broker symbols and timeframes, validates the data, prints a readable summary, and saves CSV files under `data/live/` for inspection.

Configure symbols and timeframes in `.env`:

```bash
SYMBOLS=XAUUSDm,EURUSDm,GBPUSDm
TIMEFRAMES=M1,M5,M15,H1
BARS_PER_TIMEFRAME=500
```

`SYMBOLS` and `TIMEFRAMES` are comma-separated. Use the broker's exact symbol names, including suffixes like `XAUUSDm`, when needed.

Run the Stage 2 data check:

```bash
python scripts/check_market_data.py
```

Each fetched candle DataFrame includes `is_closed_candle`. The last candle is marked `False` because it may still be forming; all previous candles are marked `True`. This matters because future signal logic should confirm signals on closed candles, keeping live behavior consistent with backtests.

Live collection compares the newest candle with both the broker's latest tick and the current clock. Newly selected symbols are retried briefly while MT5 synchronizes their history. Data that remains stale is rejected instead of being passed to analysis or paper trading.

## Stage 3 Market Analysis

Stage 3 adds a market condition analysis engine on top of the Stage 2 data collector.

It includes:

- Indicator and candle features: EMA20, EMA50, EMA200, RSI14, ATR14, candle body, range, upper wick, lower wick, and body-to-range ratio.
- Trend analysis using closed candles and EMA alignment.
- Volatility analysis using ATR14 compared with the latest 50 closed candles.
- Spread quality analysis using simple broker-dependent thresholds.
- Market regime classification: `TRENDING`, `RANGING`, `CHOPPY`, `HIGH_VOLATILITY`, `LOW_VOLATILITY`, `BAD_SPREAD`, or `UNKNOWN`.
- Multi-timeframe bias scoring across M1, M5, M15, and H1.

Run the Stage 3 analysis check:

```bash
python scripts/check_market_analysis.py
```

This stage still does not trade. It only analyzes market condition so later stages can avoid bad spread, low volatility, extreme volatility, and unclear markets.

## Stage 4 Signal Candidates

Stage 4 adds signal candidate generation and setup scoring. It does not place trades.

It provides:

- BUY, SELL, or NO_TRADE decisions.
- ELIGIBLE, WATCHLIST, or REJECTED status.
- A 0-100 setup score.
- Passed conditions, failed conditions, and rejection reasons.
- Clear diagnostics for every configured symbol and signal timeframe.

Configure signal behavior in `.env`:

```bash
SIGNAL_TIMEFRAMES=M1,M5
BIAS_TIMEFRAMES=M15,H1
MIN_SIGNAL_SCORE=70
WATCHLIST_SCORE=55
ALLOW_MIXED_BIAS=false
```

Run the Stage 4 signal check:

```bash
python scripts/check_signals.py
```

This stage is for decision transparency. The bot should explain why it would or would not take a setup, avoiding the earlier problem where no trade happened without a clear reason.

## Stage 5 Decision Journal

Stage 5 adds append-only tracking for every signal decision. It records eligible, watchlist, and rejected setups so future stages can review missed trades, rejected signals, useful filters, bad filters, and early or late decisions.

It writes two files:

- `data/logs/decision_journal.csv`: flat CSV rows for quick Excel or pandas review.
- `data/logs/signal_history.jsonl`: full structured signal events for future learning and outcome analysis.

Configure journal behavior in `.env`:

```bash
DECISION_JOURNAL_PATH=data/logs/decision_journal.csv
SIGNAL_HISTORY_PATH=data/logs/signal_history.jsonl
TRACK_WATCHLIST_SIGNALS=true
TRACK_REJECTED_SIGNALS=true
```

Run the Stage 5 journal check:

```bash
python scripts/check_signal_journal.py
```

This stage only records decisions. It does not trade. Future stages can analyze these journal records to study rejected, missed, watchlist, and eligible signal outcomes.

## Stage 6 Future Outcome Tracking

Stage 6 adds post-signal outcome tracking. It reads saved signal decisions from `data/logs/signal_history.jsonl`, fetches later candles, and checks whether each signal later made a favorable move, adverse move, both, or no clear move.

It helps identify:

- Rejected or watchlist signals that became missed good trades.
- Rejected signals where filters likely protected the account.
- Eligible signals that later moved adversely.
- Filters that may be too strict or useful.

Configure outcome tracking in `.env`:

```bash
OUTCOME_LOOKAHEAD_CANDLES=12
OUTCOME_MIN_MOVE_ATR=1.0
OUTCOME_ADVERSE_MOVE_ATR=0.7
OUTCOME_MAX_EVENTS_TO_CHECK=200
OUTCOME_REPORT_PATH=data/logs/signal_outcome_report.csv
```

Run the Stage 6 outcome check:

```bash
python scripts/check_signal_outcomes.py
```

This is not backtesting and not live trading. It is post-signal analysis only. In this simple stage, running the script multiple times may append duplicate outcome rows. A future stage can mark JSONL events as checked to avoid duplicates.

## Stage 7 Risk And Trade Plans

Stage 7 adds risk management calculations and trade plan generation. It converts signal candidates into planning-only risk summaries with entry reference, ATR-based stop loss, reward/risk take profit, risk amount, broker-aware lot size estimate, and validation issues.

It includes:

- Account balance/equity normalization.
- Percentage or fixed risk amount calculation.
- ATR-based stop distance.
- RR-based take profit.
- Broker-aware lot estimation using tick value, tick size, and volume rules.
- Trade plan validation and rejection reasons.

Configure risk planning in `.env`:

```bash
RISK_PER_TRADE_PERCENT=0.5
MAX_RISK_PER_TRADE_PERCENT=1.0
DEFAULT_RR_RATIO=2.0
MIN_RR_RATIO=1.5
ATR_SL_MULTIPLIER=1.2
ATR_TP_MULTIPLIER=2.0
USE_FIXED_RISK_AMOUNT=false
FIXED_RISK_AMOUNT=5.0
MIN_STOP_ATR_MULTIPLIER=0.8
MAX_STOP_ATR_MULTIPLIER=3.0
```

Run the Stage 7 plan check:

```bash
python scripts/check_trade_plans.py
```

This stage creates trade plans only. It does not execute orders. A valid plan only means the plan is mathematically valid; it is not permission for the bot to trade.

## Stage 8 Pre-Execution Validation

Stage 8 validates broker constraints and scalping trading costs for generated trade plans. It still does not place trades.

It checks:

- Broker stop level and freeze level information.
- Volume min/max/step constraints.
- Trade mode availability.
- Spread cost in account currency when tick value/tick size are known.
- Spread-to-ATR ratio.
- Spread-to-SL ratio.
- Spread-to-TP ratio.
- Net RR after spread.
- Margin estimate when broker margin fields are available.
- Execution-ready-later vs preview-only status.

Configure validation thresholds in `.env`:

```bash
MAX_SPREAD_TO_ATR_RATIO=0.25
MAX_SPREAD_COST_RISK_PERCENT=20.0
MAX_SPREAD_TO_SL_RATIO=0.35
MAX_SPREAD_TO_TP_RATIO=0.25
MIN_NET_RR_AFTER_SPREAD=1.2
MIN_STOP_DISTANCE_POINTS=0
MIN_TP_DISTANCE_POINTS=0
REQUIRE_ELIGIBLE_SIGNAL_FOR_EXECUTION=true
ALLOW_WATCHLIST_PLAN_PREVIEW=true
CHECK_MARGIN_REQUIREMENT=true
```

Run:

```bash
python scripts/check_pre_execution.py
```

Execution-ready-later does not mean execution is enabled. WATCHLIST plans remain preview-only. Broker thresholds are broker-dependent and should be tuned from live data before any future execution stage.

## Stage 9 Paper Execution Simulator

Stage 9 adds paper execution simulation. It does not place MT5 orders.

The simulator can:

- Create simulated entries from valid trade plans.
- Simulate SL and TP outcomes using closed candles.
- Maintain a paper trade CSV journal and JSONL event history.
- Save the latest open paper trades snapshot.
- Simulate WATCHLIST plans when enabled, which helps learn whether watchlist signals were too strict.
- Use conservative SL-first logic if TP and SL are touched in the same candle.

Run:

```bash
python scripts/check_paper_execution.py
```

This is simulation only and is safe to run repeatedly. It updates existing open paper trades before opening new ones and avoids duplicate open paper trades for the same symbol/timeframe. Paper simulation comes before any future demo execution so the strategy can be evaluated without broker orders.

## Stage 9.1 Paper Trade Status

Stage 9.1 improves paper trade monitoring and lifecycle reporting.

The important distinction:

- `data/logs/paper_trades.csv` is an opening journal.
- `data/logs/paper_trade_events.jsonl` is the source of truth for latest paper trade states.
- `data/logs/paper_trades_closed.csv` stores completed paper trades.
- `data/live/paper_status_latest.json` stores the latest open/closed/floating paper state.
- `data/logs/paper_performance_summary.csv` stores aggregate paper performance snapshots.

Run:

```bash
python scripts/check_paper_status.py
```

The report shows current open trades, closed trades, floating R/PnL, progress toward TP, win rate, total PnL, and total R. The bot still does not place real orders.

## Stage 9.2 Paper Timing Reliability

Stage 9.2 fixes paper execution timing. Paper trades now store `opened_candle_time`, `signal_candle_time`, and `last_evaluated_candle_time`.

The simulator now:

- Evaluates only closed candles after the paper trade opened.
- Scans every closed candle since the last evaluation, so TP/SL hits between script runs are not missed.
- Prevents paper trades from closing on candles that existed before the simulated entry.
- Keeps conservative SL-first logic when TP and SL are touched in the same candle.

Existing paper performance created before Stage 9.2 may be unreliable because older trades could have been evaluated against pre-entry candles. To restart paper testing cleanly, archive the old paper logs:

```bash
python scripts/reset_paper_logs.py --confirm
```

The reset helper moves existing paper files into `data/logs/archive/` instead of deleting them permanently. The bot still does not place real orders.

## Stage 10 Continuous Paper Runner

Stage 10 adds a continuous paper trading runner and clean paper performance analyzer. Manual one-shot execution can miss setups because the bot only checks the market when the command is run. The continuous runner polls MT5, waits for new closed candles when configured, updates open paper trades, opens valid paper simulations, and saves status/performance reports.

Run automatic paper testing:

```bash
python scripts/run_paper_bot.py
```

Optional short run:

```bash
python scripts/run_paper_bot.py --max-cycles 10
```

Stop the runner with `Ctrl+C`.

Analyze clean paper performance:

```bash
python scripts/check_paper_analysis.py
```

Stage 10 writes:

- `data/live/paper_bot_heartbeat.json`
- `data/logs/paper_bot_run.log`
- `data/live/paper_analysis_latest.json`
- `data/logs/paper_analysis_report.md`

This is still paper trading only. It does not place real or demo MT5 orders. Demo auto-execution comes later only after enough clean paper evidence.

Paper PnL deducts the validated entry spread. Optional `PAPER_COMMISSION_PER_LOT_ROUND_TRIP` (account currency) and `PAPER_SLIPPAGE_POINTS_PER_SIDE` (symbol points, adverse on both entry and exit) are deliberately blank by default. Enter `0` commission only when the connected MT5 account has no commission. Set a slippage stress assumption from observed fills; leaving it blank marks the trade cost model incomplete. The report counts complete and incomplete trades; a partial-cost PnL is not evidence of net profitability.

## Stage 10.1 Paper Filter Calibration

Stage 10.1 adds configurable paper-only filters for controlled experiments. These filters affect only whether an already-generated candidate is admitted to paper simulation. They do not change signal generation, signal scoring, strategy thresholds, or market analysis.

Baseline mode keeps filters disabled:

```env
PAPER_FILTERS_ENABLED=false
PAPER_EXPERIMENT_NAME=baseline
```

Example M5 SELL-only experiment:

```env
PAPER_FILTERS_ENABLED=true
PAPER_EXPERIMENT_NAME=m5_sell_only
PAPER_ALLOWED_SYMBOLS=EURUSDm,GBPUSDm
PAPER_ALLOWED_TIMEFRAMES=M5
PAPER_ALLOWED_DIRECTIONS=SELL
PAPER_MIN_SIGNAL_SCORE=55
PAPER_ALLOWED_SIGNAL_STATUSES=WATCHLIST,ELIGIBLE
PAPER_REQUIRE_COSTS_VALID=true
PAPER_REQUIRE_BROKER_CONSTRAINTS_VALID=true
```

Archive the completed baseline before starting a new experiment:

```bash
python scripts/reset_paper_logs.py --confirm --label baseline_51_trades
```

Start the filtered paper runner and compare reports by experiment:

```bash
python scripts/run_paper_bot.py
python scripts/check_paper_analysis.py
```

Paper filter metadata is stored with each trade and analysis includes a `By Experiment` breakdown. Do not use these experimental filters for demo or live execution. This stage remains paper-only.

## Fixing MT5 IPC timeout (-10005)

If `python main.py` fails with `(-10005, 'IPC timeout')`, MT5 and Python could not communicate through the local terminal process.

Try these steps:

- Open MT5 manually first.
- Confirm the account is logged in.
- Confirm Market Watch prices are moving.
- Set `MT5_PATH` to `terminal64.exe`, not a shortcut.
- Use the same Windows permission level for MT5 and Python.
- Close duplicate MT5 terminals.
- Restart MT5 and try again.
- Run `python scripts/check_mt5_connection.py`.

The connection check script prints the configured MT5 path, terminal details, account details, and whether the default symbol is visible.

## Run Tests

```bash
pytest
```

## Safety Note

Stage 1 does not place trades, create orders, modify positions, or perform any live execution.
