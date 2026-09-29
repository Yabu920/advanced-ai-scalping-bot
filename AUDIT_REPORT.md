# Advanced AI Scalping Bot Audit Report

Audit date: 2026-05-26

Scope: Stage 1 through Stage 9.1. This audit reviewed code, tests, scripts, safety posture, paper trading artifacts, and current paper performance. No strategy thresholds or execution logic were changed.

## Executive Summary

The project remains paper/simulation-only. A full text search found no `mt5.order_send`, `order_check`, `TRADE_ACTION`, or real order execution path. The architecture is modular and each stage has focused tests. The main technical concern before Stage 10 is paper execution timing accuracy: some closed paper trades have `close_time_utc` earlier than `created_time_utc`, so paper outcome evaluation can be using candles that existed before the simulated trade was opened.

Overall status:

- Safety: PASS
- Architecture: PASS
- Data collection: PASS
- Signal transparency: PASS
- Risk and broker validation: PASS with tuning warnings
- Paper execution: WARNING
- Paper performance quality: WARNING / NEEDS MORE DATA

## Dangerous Code Check

Searches performed:

- `order_send`, `OrderSend`, `order_check`, `TRADE_ACTION`, `mt5.order`
- credential-related strings
- real order/execution language

Findings:

- No `mt5.order_send` found.
- No `order_check` found.
- No `TRADE_ACTION` constants found.
- No real MT5 order creation module found.
- No source-code hardcoded password found.
- Local `.env` contains credentials as expected for local operation and is ignored by `.gitignore`.
- `data/logs/bot.log` contains the MT5 account login number many times. This is not a trading-safety issue, but it is a privacy/log hygiene warning.

Conclusion: The bot is still paper/simulation only.

## Stage-by-Stage Review

### Stage 1 Foundation

Files involved:

- `main.py`
- `config/settings.py`
- `config/symbols.py`
- `config/timeframes.py`
- `mt5/connection.py`
- `mt5/market_data.py`
- `strategy/indicators.py`
- `strategy/diagnostics.py`
- `utils/logger.py`
- `utils/time_utils.py`

What works:

- Environment-based settings load correctly.
- MT5 initialization is defensive and logs common IPC/authorization errors.
- No password is printed.
- Basic candle collection and indicator diagnostics work.
- Main runner exits safely on MT5/data failures.

What could be wrong:

- Scripts auto-connect to MT5 by design; there is no explicit `--connect` confirmation mode.
- Account login number appears in logs.

Edge cases:

- MT5 IPC timeout still depends on terminal state.
- Broker suffix case had to be preserved and is now handled.

Safety concerns:

- No trading execution.
- Log privacy warning for account number.

Tests:

- Indicator tests exist.
- Settings tests exist.

Readiness:

- PASS.

### Stage 2 Data Collection

Files involved:

- `mt5/market_data.py`
- `strategy/data_validation.py`
- `strategy/data_summary.py`
- `scripts/check_market_data.py`
- `config/settings.py`

What works:

- Multi-symbol and multi-timeframe data collection works.
- `is_closed_candle` marks the final forming candle as `False`.
- Validation checks required OHLC columns, sorting, duplicates, high/low sanity, row count, and closed-candle field.
- CSV snapshots are saved under `data/live/`.

What could be wrong:

- `copy_rates_from_pos(..., 0, bars)` includes the currently forming candle, which is acceptable because it is marked as not closed.
- Data validity requires at least 50 rows; thinner timeframes/settings may fail intentionally.

Edge cases:

- One symbol/timeframe can fail without breaking the entire collection.
- Suffix and case-sensitive broker names are preserved.

Safety concerns:

- Read-only market data.

Tests:

- Data validation tests exist.
- Settings list parsing tests exist.

Readiness:

- PASS.

### Stage 3 Market Analysis

Files involved:

- `strategy/indicators.py`
- `strategy/trend_analysis.py`
- `strategy/volatility_analysis.py`
- `strategy/spread_analysis.py`
- `strategy/market_regime.py`
- `strategy/market_analyzer.py`
- `strategy/market_summary.py`
- `scripts/check_market_analysis.py`

What works:

- Adds full indicators and candle features.
- Trend uses latest closed candle.
- Volatility compares latest ATR against a 50-candle ATR average.
- Spread quality rules are symbol-aware at a simple Stage 3 level.
- Regime classification separates bad spread, low volatility, high volatility, ranging, choppy, trending, and unknown.

What could be wrong:

- Spread thresholds are simple and broker-dependent.
- Volatility categories are ATR-ratio based only.
- Market regime does not yet use session, news, or structure.

Edge cases:

- Missing indicators return neutral/unknown analysis rather than crashing.
- Not enough ATR data returns unknown volatility.

Safety concerns:

- Analysis only.

Tests:

- Trend, volatility, spread, and regime tests exist.

Readiness:

- PASS with threshold-tuning warning.

### Stage 4 Signal Scoring

Files involved:

- `strategy/signal_types.py`
- `strategy/signal_rules.py`
- `strategy/setup_scoring.py`
- `strategy/signal_engine.py`
- `strategy/signal_summary.py`
- `scripts/check_signals.py`

What works:

- Every configured symbol/timeframe produces an explained decision.
- Directions are derived from higher-timeframe bias.
- Mixed/neutral bias is rejected when `ALLOW_MIXED_BIAS=false`.
- EMA, RSI, regime, volatility, and bias confidence contribute to score.
- Hard rejections override scores.

What could be wrong:

- Bias confidence of 40 can still allow directional WATCHLIST signals.
- M1/M5 entries can be noisy with current simple EMA/RSI logic.
- No session filter or structure filter yet.

Edge cases:

- Missing data produces `NO_TRADE` with `INSUFFICIENT_DATA`.
- EMA/RSI failures reduce score but are not always hard rejects.

Safety concerns:

- Signals only, no execution.

Tests:

- Signal rules and setup scoring tests exist.

Readiness:

- PASS for diagnostics.
- WARNING for live-readiness because current paper results suggest WATCHLIST signals are weak.

### Stage 5 Decision Journal

Files involved:

- `journal/decision_journal.py`
- `journal/signal_tracker.py`
- `journal/journal_summary.py`
- `scripts/check_signal_journal.py`

What works:

- CSV journal records flat decision summaries.
- JSONL stores full structured signal details.
- ELIGIBLE, WATCHLIST, and REJECTED can be tracked.
- Full decision context is preserved for later learning.

What could be wrong:

- CSV is append-only and can grow noisy.
- It does not deduplicate decisions, which is acceptable for a run journal.

Edge cases:

- Missing nested fields are handled defensively.
- JSON-safe conversion is implemented.

Safety concerns:

- Records decisions only.

Tests:

- Decision journal and signal tracker tests exist.

Readiness:

- PASS.

### Stage 6 Outcome Tracking

Files involved:

- `learning/outcome_types.py`
- `learning/signal_outcome.py`
- `learning/outcome_tracker.py`
- `learning/outcome_summary.py`
- `scripts/check_signal_outcomes.py`

What works:

- Recent signal JSONL events are read safely.
- Invalid JSON lines are ignored.
- Future favorable/adverse moves are classified.
- Outcome CSV is append-only.

What could be wrong:

- Events are not marked as checked, so duplicate outcome rows can be appended.
- Outcome matching relies on available future candles and signal timestamps.

Edge cases:

- Fresh signals produce `INSUFFICIENT_FUTURE_DATA`, which is expected.
- Unknown direction is handled.

Safety concerns:

- Post-signal analysis only.

Tests:

- Signal outcome and outcome tracker tests exist.

Readiness:

- PASS for simple post-signal analysis.
- WARNING for duplicate outcome rows until event marking is implemented.

### Stage 7 Trade Plan Builder

Files involved:

- `risk/account.py`
- `risk/sl_tp.py`
- `risk/lot_size.py`
- `risk/trade_plan.py`
- `risk/trade_plan_summary.py`
- `scripts/check_trade_plans.py`

What works:

- Risk amount can be percentage or fixed.
- ATR-based SL distance and RR-based TP are produced.
- Lot sizing uses broker tick size/value when available.
- Missing tick value/tick size safely rejects lot estimation.
- WATCHLIST plans are preview-only.

What could be wrong:

- ATR SL/TP can be too tight for scalping costs before Stage 8 validation.
- No real margin calculation through broker API.

Edge cases:

- Rejected signals produce invalid/no executable plans.
- Missing ATR/entry makes plans invalid.

Safety concerns:

- Plans only.
- No execution permission.

Tests:

- Risk account, SL/TP, lot size, and trade plan tests exist.

Readiness:

- PASS as mathematical plan builder.

### Stage 8 Broker/Cost Validation

Files involved:

- `mt5/symbols.py`
- `risk/broker_constraints.py`
- `risk/trading_costs.py`
- `risk/margin_check.py`
- `risk/pre_execution_validator.py`
- `risk/pre_execution_summary.py`
- `scripts/check_pre_execution.py`

What works:

- Broker stop distance, volume rules, trade mode, spread cost, spread ratios, net RR after spread, and margin estimate are validated.
- WATCHLIST remains preview-only.
- Execution-ready-later is separated from trading permission.

What could be wrong:

- Cost validator appears intentionally strict; current paper plans often fail cost ratios or net RR checks.
- Margin often remains unknown because broker margin fields are unavailable; this is handled as warning.

Edge cases:

- Missing tick value/tick size makes spread cost unknown.
- Unknown trade mode warns rather than aggressively failing.

Safety concerns:

- Validation only.
- No order send.

Tests:

- Broker constraints, trading costs, margin, and pre-execution validator tests exist.

Readiness:

- PASS for validation.
- WARNING: thresholds need live-data tuning before real execution.

### Stage 9 Paper Execution

Files involved:

- `paper/paper_trade.py`
- `paper/paper_engine.py`
- `paper/paper_journal.py`
- `paper/paper_summary.py`
- `scripts/check_paper_execution.py`

What works:

- Paper trades are simulated only.
- Duplicate open trades are blocked by symbol/timeframe.
- Max open trades and per-symbol limits exist.
- WATCHLIST paper simulation is configurable.
- TP/SL closes are simulated.
- If TP and SL hit same candle, SL is selected first.

What could be wrong:

- Clear bug: paper trade close times can be earlier than `created_time_utc`. Current open/close simulation can evaluate a latest closed candle that predates the paper trade creation. This makes paper performance unreliable until fixed.
- Updates use only the latest closed candle, not every candle since the paper trade opened, so TP/SL hits between script runs can be missed.
- Paper trades are based on current generated plans, not an explicit bar-by-bar event stream.

Edge cases:

- Invalid plans produce no paper trade.
- Duplicate symbol/timeframe open trades are prevented.

Safety concerns:

- Paper only.
- No MT5 orders.

Tests:

- Paper trade, paper engine, and paper journal tests exist.

Readiness:

- WARNING. The simulator structure is good, but timing/candle sequencing must be fixed before trusting performance.

### Stage 9.1 Paper Status and Performance Reporting

Files involved:

- `paper/paper_monitor.py`
- `paper/paper_performance.py`
- `paper/paper_status_summary.py`
- `paper/paper_journal.py`
- `scripts/check_paper_status.py`

What works:

- JSONL event sourcing reconstructs latest trade states.
- Open/closed trades are separated correctly.
- Closed-trade CSV avoids duplicate paper trade IDs.
- Floating R/PnL is calculated for open trades.
- Performance is grouped by symbol and timeframe.

What could be wrong:

- Performance depends on Stage 9 closure correctness, which currently has timing concerns.
- `paper_trades.csv` remains an opening log, not a state table; this is now documented and acceptable.

Edge cases:

- Invalid JSON lines are ignored.
- Missing market data leaves floating metrics unavailable.

Safety concerns:

- Reporting only.

Tests:

- Paper monitor, performance, and enhanced journal tests exist.

Readiness:

- PASS for reporting mechanics.
- WARNING for performance reliability until Stage 9 timing bug is fixed.

## Paper Trading Logic Review

Duplicate open trades:

- PASS. `PaperExecutionEngine.should_create_paper_trade` checks existing open trades by symbol/timeframe.
- PASS. It also enforces total open trade and per-symbol limits.

TP/SL closure:

- PASS for unit-tested candle cases.
- WARNING in live journal: close timestamps can predate creation timestamps.

Same-candle TP/SL:

- PASS. Conservative SL-first logic exists and is tested.

JSONL reconstruction:

- PASS. `reconstruct_latest_trade_states` keeps latest event per `paper_trade_id`.

CSV vs JSONL:

- PASS with documentation. `paper_trades.csv` is an opening journal; `paper_trade_events.jsonl` is source of truth.

Closed trade deduplication:

- PASS. `append_closed_trades_csv` avoids duplicate `paper_trade_id` rows.

## Signal Quality Review

WATCHLIST paper trading:

- Yes. All closed paper trades in the current report are WATCHLIST signals.
- Current WATCHLIST paper performance is poor: 1 win, 6 losses, -4.0R.

ELIGIBLE signals:

- ELIGIBLE signals appear rare or absent in current paper history.
- Likely causes: minimum score threshold, hard rejections, cost validation, low/mixed bias confidence, and regime filters.

M1 signal quality:

- Current closed M1 paper trades: 3 losses, -3R.
- WARNING: M1 appears noisy with current logic.

M5 signal quality:

- Current closed M5 paper trades: 1 win, 3 losses, -1R.
- M5 appears better than M1 in this tiny sample, but still negative.

Bias confidence:

- Low-confidence directional bias can still create WATCHLIST signals.
- Current EURUSD bearish confidence of 40 has allowed WATCHLIST behavior in prior runs.

Mixed/neutral bias:

- PASS. With `ALLOW_MIXED_BIAS=false`, mixed and neutral bias signals are rejected.

## Risk Quality Review

Risk amount:

- PASS. Percentage and fixed risk are supported. Missing account defaults safely to zero risk.

Lot sizing:

- PASS. Uses tick size/value and volume min/max/step.
- PASS. It does not guess dangerous lot sizes when tick value/tick size are missing.

SL/TP distances:

- PASS mathematically.
- PASS broker stop-level validation exists.
- WARNING: practical scalping SL/TP may still be too tight after spread/cost checks.

Spread/cost checks:

- PASS. Spread cost, spread-to-ATR, spread-to-SL, spread-to-TP, and net RR after spread are calculated.
- WARNING: Current cost validation often rejects plans or shows high cost load, which may be correctly strict.

Net RR after spread:

- PASS. Implemented in `risk/trading_costs.py`.

## Data Quality Review

Closed candles:

- PASS. Last candle is marked `is_closed_candle=False`.
- PASS. Signal/trend logic uses latest closed candle.

Timestamps:

- WARNING. Data timestamps are UTC pandas timestamps, but paper trade `created_time_utc` is wall-clock UTC. Paper close logic can currently close using candles earlier than creation time.

Multi-symbol isolation:

- PASS. Data structures are nested by symbol/timeframe.
- PASS. Paper duplicate checks are symbol/timeframe scoped.

## Paper Performance Summary

Files read:

- `data/logs/paper_trades.csv`
- `data/logs/paper_trade_events.jsonl`
- `data/logs/paper_trades_closed.csv`
- `data/logs/paper_performance_summary.csv`
- `data/live/paper_status_latest.json`

Current source-of-truth state from `paper_status_latest.json`:

- Open trades: 2
- Closed trades: 7
- Closed TP: 1
- Closed SL: 6
- Total PnL: -$20.00
- Total R: -4.0R
- Win rate: 14.3%

Performance by symbol:

- EURUSDm: 3 closed, 0 wins, 3 losses, -3.0R, -$15.00
- GBPUSDm: 4 closed, 1 win, 3 losses, -1.0R, -$5.00

Performance by timeframe:

- M1: 3 closed, 0 wins, 3 losses, -3.0R, -$15.00
- M5: 4 closed, 1 win, 3 losses, -1.0R, -$5.00

Performance by signal status:

- WATCHLIST: 7 closed, 1 win, 6 losses, -4.0R, -$20.00
- ELIGIBLE: 0 closed, no data
- REJECTED: 0 closed, rejected signals are not paper simulated

Interpretation:

- NEEDS MORE DATA, but current WATCHLIST simulations are weak.
- M5 is less bad than M1 in this small sample.
- No ELIGIBLE sample exists, so ELIGIBLE quality cannot be assessed.

## Stage 10 Gating Questions

1. Why are ELIGIBLE signals not appearing?
   - Likely because score rarely reaches `MIN_SIGNAL_SCORE=70` after hard filters, bias confidence, regime checks, EMA/RSI scoring, and Stage 8 cost validation. This is a signal quality/tuning question, not a code failure.

2. Are WATCHLIST signals too weak for paper trading?
   - WARNING. Current WATCHLIST paper trades are 1 win and 6 losses, -4.0R. Sample is small but poor.

3. Should M1 be disabled for entries?
   - WARNING / NEEDS MORE DATA. Current M1 paper results are 0 wins, 3 losses, -3R. M1 appears noisy.

4. Should M5 become the main entry timeframe?
   - NEEDS MORE DATA. Current M5 is better than M1 but still negative: 1 win, 3 losses, -1R.

5. Should bias confidence minimum be increased?
   - WARNING. Low-confidence directional bias can permit WATCHLIST signals. Consider requiring stronger H1/M15 agreement before paper simulation, but do not change thresholds until Stage 10 design.

6. Are paper trade closures correct?
   - FAIL/WARNING. Unit closure rules are correct, but live paper records show close times earlier than creation times, so event timing is not reliable.

7. Is the paper performance report accurate?
   - WARNING. The report accurately summarizes current JSONL state, but the underlying paper closure timing bug makes performance conclusions unreliable.

8. Are duplicate trades fully controlled?
   - PASS for duplicate currently open symbol/timeframe trades.
   - WARNING for repeated same setup over time after closure, which may be acceptable but needs policy.

9. Is the cost validator too strict or correctly strict?
   - NEEDS MORE DATA. It is correctly strict for safety. Current results suggest spread/cost burden is material.

10. Are SL/TP distances too tight?
   - WARNING. Stage 8 has flagged high spread-to-SL/TP ratios in prior runs. Current paper losses also suggest stop/entry logic may be too tight or entries too noisy.

## Final Audit Classification

| Area | Status | Notes |
|---|---|---|
| No real trading / order safety | PASS | No order APIs found. |
| Configuration | PASS | Broad settings coverage; local `.env` contains secrets as expected. |
| Log privacy | WARNING | Account login appears in `bot.log`. |
| MT5 connection | PASS | Works, but IPC depends on terminal health. |
| Market data collection | PASS | Multi-symbol/timeframe and closed-candle flags work. |
| Data validation | PASS | Good basic OHLC validation. |
| Market analysis | PASS | Good diagnostic layer; thresholds need tuning. |
| Signal scoring | WARNING | Transparent, but WATCHLIST quality appears weak. |
| Decision journal | PASS | Good CSV/JSONL structure. |
| Outcome tracking | WARNING | Duplicate appends possible; expected for current stage. |
| Trade plans | PASS | Safe mathematical plans only. |
| Broker/cost validation | PASS | Safety-first; may be strict. |
| Paper execution | WARNING/FAIL | Structure is good, but candle timing bug affects performance trust. |
| Paper status reporting | PASS | Correctly reconstructs state from JSONL. |
| Paper performance | WARNING | Report mechanics work; data reliability affected by paper timing bug and small sample. |

## Recommended Fixes Before Stage 10

1. Fix paper execution time sequencing.
   - Paper trades should store the signal/latest candle time as an `opened_candle_time`.
   - Update logic should evaluate only candles after that open candle time.
   - Never close a paper trade on a candle with `time <= opened_candle_time`.

2. Update open paper trades across all candles since entry, not only the latest closed candle.
   - Current logic can miss TP/SL hits between script runs.

3. Add `opened_candle_time`, `entry_candle_time`, or `signal_candle_time` to paper trade records.
   - This will make outcome/performance reports auditable.

4. Add paper performance filters by `source`, `signal_status`, rejection context, and score band.
   - Needed to answer whether WATCHLIST simulation is useful.

5. Add a policy for repeated same symbol/timeframe setups after closure.
   - Current duplicate prevention only blocks currently open duplicates.

6. Consider masking account login in logs.
   - Not required for trading safety, but recommended for privacy.

7. Do not proceed to real/demo execution until paper timing is fixed and a larger sample is collected.

