# Post Stage 9.2 Readiness Report

Date: 2026-05-26

## Executive Summary

The project is still paper/simulation only. Stage 9.2 fixed the key paper execution timing bug by storing entry candle timing on paper trades, scanning only closed candles after entry, and preventing closes from pre-entry candles.

Overall readiness: **PASS for clean paper testing**, with **NEEDS MORE DATA** for strategy quality decisions.

Do not judge strategy performance from pre-9.2 paper logs. Those logs may contain unreliable paper closes from candles that existed before simulated trade entry.

## 1. Current Project Stage Status

### Stage 1: Foundation

Status: **PASS**

Important files:
- `main.py`
- `config/settings.py`
- `config/symbols.py`
- `config/timeframes.py`
- `mt5/connection.py`
- `utils/logger.py`

What works:
- Modular project structure exists.
- Settings load safely from environment variables.
- MT5 connection supports explicit terminal path and already logged-in terminals.
- Logging writes to console and `data/logs/bot.log`.

Known limitations:
- MT5 connectivity still depends on the local terminal being open, logged in, and reachable.
- IPC timeout can still happen if MT5 and Python cannot communicate.

Safety:
- Safe. No trading execution exists.

### Stage 2: Market Data Collection

Status: **PASS**

Important files:
- `mt5/market_data.py`
- `strategy/data_validation.py`
- `strategy/data_summary.py`
- `scripts/check_market_data.py`

What works:
- Multi-symbol and multi-timeframe OHLC collection exists.
- DataFrames include `requested_symbol`, `broker_symbol`, `timeframe`, and `is_closed_candle`.
- Last candle is marked as forming with `is_closed_candle = False`; previous candles are closed.
- Validation checks OHLC integrity, duplicates, ordering, and required columns.

Known limitations:
- Collection depends on MT5 availability.
- Broker symbol suffix handling remains basic but usable for configured broker names.

Safety:
- Safe. Data collection only.

### Stage 3: Market Analysis

Status: **PASS**

Important files:
- `strategy/indicators.py`
- `strategy/trend_analysis.py`
- `strategy/volatility_analysis.py`
- `strategy/spread_analysis.py`
- `strategy/market_regime.py`
- `strategy/market_analyzer.py`
- `strategy/market_summary.py`
- `scripts/check_market_analysis.py`

What works:
- EMA, RSI, ATR, candle features, spread quality, volatility, trend, regime, and multi-timeframe bias are calculated.
- Analysis uses closed candles for confirmation.
- Regime blocks bad spread, low volatility, and extreme volatility.

Known limitations:
- Spread thresholds are static and broker-dependent.
- Regime logic is deliberately simple and not yet optimized.

Safety:
- Safe. Analysis only.

### Stage 4: Signal Scoring

Status: **PASS / NEEDS MORE DATA**

Important files:
- `strategy/signal_types.py`
- `strategy/signal_rules.py`
- `strategy/setup_scoring.py`
- `strategy/signal_engine.py`
- `strategy/signal_summary.py`
- `scripts/check_signals.py`

What works:
- Every symbol/timeframe produces a decision: `BUY`, `SELL`, or `NO_TRADE`.
- Signals include score, status, passed conditions, failed conditions, and rejection reasons.
- Mixed and neutral bias are rejected unless explicitly allowed.

Known limitations:
- `ELIGIBLE` signals may be rare because score must reach `MIN_SIGNAL_SCORE=70` and hard rejections override score.
- `M1` can produce noisy setup changes.
- `WATCHLIST` signals are intentionally allowed for learning, not execution.

Safety:
- Safe. Signal generation only.

### Stage 5: Decision Journal

Status: **PASS**

Important files:
- `journal/decision_journal.py`
- `journal/signal_tracker.py`
- `journal/journal_summary.py`
- `scripts/check_signal_journal.py`

What works:
- Signal decisions can be appended to CSV and JSONL.
- Rejected, watchlist, and eligible signals can be tracked.
- Full structured signal details are preserved for later learning.

Known limitations:
- Journal grows append-only.
- No deduplication of signal decisions across repeated runs yet.

Safety:
- Safe. Records decisions only.

### Stage 6: Signal Outcome Tracking

Status: **PASS / NEEDS MORE DATA**

Important files:
- `learning/outcome_types.py`
- `learning/signal_outcome.py`
- `learning/outcome_tracker.py`
- `learning/outcome_summary.py`
- `scripts/check_signal_outcomes.py`

What works:
- Saved signal events can be evaluated against future candles.
- Outcomes classify favorable move, adverse move, no clear move, and insufficient data.
- Learning labels identify missed good trades, correct rejections, and bad eligible signals.

Known limitations:
- Events are not marked as checked yet, so reports can duplicate on repeated runs.
- Fresh signals often produce `INSUFFICIENT_FUTURE_DATA`.

Safety:
- Safe. Post-signal analysis only.

### Stage 7: Trade Plan Builder

Status: **PASS**

Important files:
- `risk/account.py`
- `risk/sl_tp.py`
- `risk/lot_size.py`
- `risk/trade_plan.py`
- `risk/trade_plan_summary.py`
- `scripts/check_trade_plans.py`

What works:
- Builds mathematical trade plans from valid signals.
- Calculates ATR-based SL, RR-based TP, risk amount, and broker-aware lot size.
- Refuses unsafe lot estimation when tick value or tick size is missing.

Known limitations:
- A valid plan is not execution permission.
- Plan quality depends on upstream signal quality and broker symbol info.

Safety:
- Safe. Planning only.

### Stage 8: Broker/Cost Validation

Status: **PASS**

Important files:
- `risk/broker_constraints.py`
- `risk/trading_costs.py`
- `risk/margin_check.py`
- `risk/pre_execution_validator.py`
- `risk/pre_execution_summary.py`
- `scripts/check_pre_execution.py`

What works:
- Validates stop distance, TP distance, volume min/max/step, trade mode, spread costs, spread ratios, net RR after spread, and margin where available.
- Separates plan validity, broker constraints, cost efficiency, and execution-ready-later status.
- `WATCHLIST` remains preview-only.

Known limitations:
- Margin estimate is conservative and often unknown without broker-side calculation.
- Cost thresholds need live sample tuning later.

Safety:
- Safe. Does not execute orders.

### Stage 9: Paper Execution Simulator

Status: **PASS after Stage 9.2 fix**

Important files:
- `paper/paper_trade.py`
- `paper/paper_engine.py`
- `paper/paper_journal.py`
- `paper/paper_summary.py`
- `scripts/check_paper_execution.py`

What works:
- Creates simulated trades from valid `ELIGIBLE` plans and, by configuration, valid `WATCHLIST` previews.
- Prevents duplicate open paper trades by symbol/timeframe.
- Simulates TP/SL without MT5 orders.

Known limitations:
- Paper fills are simplified and do not model slippage, commissions, partial fills, or bid/ask execution.
- Pre-9.2 paper results may be unreliable.

Safety:
- Safe. Simulation only.

### Stage 9.1: Paper Status Reporting

Status: **PASS**

Important files:
- `paper/paper_monitor.py`
- `paper/paper_performance.py`
- `paper/paper_status_summary.py`
- `scripts/check_paper_status.py`

What works:
- Reconstructs latest trade state from JSONL event history.
- Separates open trades and closed trades.
- Reports floating R/PnL, closed PnL, win rate, total R, symbol grouping, and timeframe grouping.
- Closed trade CSV avoids duplicate closed rows by `paper_trade_id`.

Known limitations:
- Accuracy depends on valid paper events; pre-9.2 events should be archived and excluded from strategy judgment.

Safety:
- Safe. Reporting only.

### Stage 9.2: Paper Timing Fix

Status: **PASS**

Important files:
- `paper/paper_trade.py`
- `paper/paper_engine.py`
- `paper/paper_journal.py`
- `risk/trade_plan.py`
- `tests/test_paper_timing.py`
- `scripts/reset_paper_logs.py`

What works:
- Paper trades store `opened_candle_time`, `signal_candle_time`, and `last_evaluated_candle_time`.
- Paper execution scans all closed candles after the last evaluated candle.
- Candles before or equal to `opened_candle_time` are ignored.
- `last_evaluated_candle_time` is updated as candles are processed.
- Same-candle TP/SL remains conservative SL-first.
- Reset helper archives old paper logs instead of deleting them.

Known limitations:
- Existing pre-9.2 paper data should not be used for performance conclusions.

Safety:
- Safe. Reliability fix only.

## 2. Stage 9.2 Timing Fix Confirmation

Confirmed in `paper/paper_trade.py`:
- `opened_candle_time`, `signal_candle_time`, and `last_evaluated_candle_time` are added when a paper trade is built.
- Timing is extracted from plan fields such as `opened_candle_time`, `signal_candle_time`, `latest_time`, `latest_candle_time`, and nested signal details when available.
- If no candle time exists, `created_time_utc` is used as fallback.

Confirmed in `paper/paper_engine.py`:
- `get_closed_candles_after_time()` filters for closed candles and returns only candles with `time > after_time`.
- `update_open_trade_with_candles()` sorts candles ascending and skips candles with `time <= opened_candle_time`.
- It also skips candles with `time <= last_evaluated_candle_time`.
- It updates `last_evaluated_candle_time` while scanning.
- It prevents invalid closes before `created_time_utc`.
- It prevents closes at or before `opened_candle_time`.
- It closes on the first TP/SL event after entry.
- Same-candle TP/SL closes as `CLOSED_SL` with conservative SL-first reasoning.

Confirmed in tests:
- `tests/test_paper_timing.py` covers opened candle time creation, pre-entry candle skipping, equal-time candle skipping, multi-candle scan, last evaluated update, close time ordering, and same-candle SL-first behavior.

## 3. Safety Verification

Search terms checked:
- `mt5.order_send`
- `order_send`
- `order_check`
- `TRADE_ACTION`
- `live order`
- `real order`
- `execution module`

Result:
- No real order-sending code was found.
- No MT5 order execution module exists.
- No `mt5.order_send` call exists.
- No `order_check` call exists.
- The project remains paper/simulation only.

Safety conclusion: **PASS**

## 4. Log and Archive Status

Checked paths:
- `data/logs/archive/`: exists
- `data/logs/archive/paper_logs_20260526_181630/`: exists
- `data/logs/paper_trades.csv`: missing from active logs
- `data/logs/paper_trade_events.jsonl`: missing from active logs
- `data/logs/paper_trades_closed.csv`: missing from active logs
- `data/logs/paper_performance_summary.csv`: missing from active logs
- `data/live/paper_status_latest.json`: missing from active live output
- `data/live/paper_execution_latest.json`: missing from active live output

Archived files found:
- `paper_execution_latest.json`
- `paper_performance_summary.csv`
- `paper_status_latest.json`
- `paper_trades.csv`
- `paper_trades_closed.csv`
- `paper_trades_open_latest.json`
- `paper_trade_events.jsonl`

Conclusion:
- Old paper logs appear to be archived.
- Active paper logs are clean/empty because the active files are currently absent.
- New paper testing can start cleanly.
- Do not use archived pre-9.2 paper performance to judge the strategy.

## 5. Configuration Review

Important `.env.example` settings:

Market universe:
- `SYMBOLS=XAUUSDm,EURUSDm,GBPUSDm`
- `TIMEFRAMES=M1,M5,M15,H1`
- `BARS_PER_TIMEFRAME=500`

Signal configuration:
- `SIGNAL_TIMEFRAMES=M1,M5`
- `BIAS_TIMEFRAMES=M15,H1`
- `MIN_SIGNAL_SCORE=70`
- `WATCHLIST_SCORE=55`
- `ALLOW_MIXED_BIAS=false`

Risk settings:
- `RISK_PER_TRADE_PERCENT=0.5`
- `MAX_RISK_PER_TRADE_PERCENT=1.0`
- `DEFAULT_RR_RATIO=2.0`
- `MIN_RR_RATIO=1.5`
- `ATR_SL_MULTIPLIER=1.2`
- `ATR_TP_MULTIPLIER=2.0`
- `USE_FIXED_RISK_AMOUNT=false`
- `FIXED_RISK_AMOUNT=5.0`
- `MIN_STOP_ATR_MULTIPLIER=0.8`
- `MAX_STOP_ATR_MULTIPLIER=3.0`

Broker/cost validation:
- `MAX_SPREAD_TO_ATR_RATIO=0.25`
- `MAX_SPREAD_COST_RISK_PERCENT=20.0`
- `MAX_SPREAD_TO_SL_RATIO=0.35`
- `MAX_SPREAD_TO_TP_RATIO=0.25`
- `MIN_NET_RR_AFTER_SPREAD=1.2`
- `MIN_STOP_DISTANCE_POINTS=0`
- `MIN_TP_DISTANCE_POINTS=0`
- `REQUIRE_ELIGIBLE_SIGNAL_FOR_EXECUTION=true`
- `ALLOW_WATCHLIST_PLAN_PREVIEW=true`
- `CHECK_MARGIN_REQUIREMENT=true`

Paper trading:
- `PAPER_TRADING_ENABLED=true`
- `PAPER_TRADE_ELIGIBLE_ONLY=false`
- `PAPER_INCLUDE_WATCHLIST=true`
- `PAPER_MAX_OPEN_TRADES=5`
- `PAPER_MAX_OPEN_TRADES_PER_SYMBOL=1`
- `PAPER_USE_PRE_EXECUTION_VALIDATION=true`

Settings that can make signals `WATCHLIST` instead of `ELIGIBLE`:
- `MIN_SIGNAL_SCORE=70`: eligible threshold is relatively high for simple Stage 4 scoring.
- `WATCHLIST_SCORE=55`: signals between 55 and 69 become watchlist.
- `ALLOW_MIXED_BIAS=false`: mixed bias hard-rejects signals.
- Hard rejections: bad spread, low volatility, mixed bias, neutral bias, and insufficient data override score.
- Broker/cost validation can prevent paper simulation even when a signal has a score.

## 6. Strategy Readiness Review

Why `ELIGIBLE` signals may be rare:
- A signal needs directional bias, bias confidence, tradable regime, EMA alignment, RSI confirmation, and acceptable volatility to reach 70+.
- Hard filters can reject a setup even when part of the score is strong.
- Higher timeframe bias can be mixed or neutral, especially when H1 and M15 disagree.
- Bad spread or low volatility makes the timeframe non-tradable.

Why `WATCHLIST` signals are allowed for paper simulation:
- `PAPER_TRADE_ELIGIBLE_ONLY=false` and `PAPER_INCLUDE_WATCHLIST=true`.
- This is useful for learning whether Stage 4 scoring is too strict.
- WATCHLIST simulation remains preview-only and does not imply future real execution permission.

Why M1 may be noisy:
- M1 candles react quickly to spread changes, small pullbacks, and short volatility bursts.
- EMA/RSI confirmation can flip frequently.
- Spread cost matters more on very short targets.

Why M5 may be better for paper testing:
- M5 usually has less candle noise than M1.
- M5 can still support scalping while giving indicators more stable structure.
- M5 may reduce false entries caused by M1 micro-fluctuations.

XAUUSDm spread risk:
- XAUUSD-like symbols are classified with `good <= 80`, `acceptable <= 150`, and `high > 150` spread points.
- Previous observed XAUUSDm spreads around 300+ points correctly trigger `BAD_SPREAD`.
- Keeping XAUUSDm enabled is useful for monitoring, but paper trades should remain blocked when spread is bad.

Mixed/neutral bias:
- Mixed bias is rejected when `ALLOW_MIXED_BIAS=false`.
- Neutral bias is rejected.
- This behavior is correct for the current staged design.

## 7. Recommended Clean Testing Procedure

1. Confirm active paper logs are clean or archived.
2. Run `pytest`.
3. Run `python scripts/check_market_data.py`.
4. Run `python scripts/check_market_analysis.py`.
5. Run `python scripts/check_signals.py`.
6. Run `python scripts/check_pre_execution.py`.
7. During an active session, run `python scripts/check_paper_execution.py` every 5 minutes.
8. After each paper execution run, run `python scripts/check_paper_status.py`.
9. Collect at least 20 clean paper trades before judging strategy behavior.
10. Review performance by symbol, timeframe, signal status, and rejection reason.
11. Do not use archived pre-9.2 paper results for strategy conclusions.

## 8. Key Questions Before Next Stage

Should we start fresh paper testing now?

Answer: **Yes.** Active paper logs are clean and Stage 9.2 timing tests pass.

Should we disable M1 paper entries temporarily?

Answer: **Not immediately.** Keep M1 enabled for the first clean sample so there is evidence. If M1 produces noisy losses or many weak watchlist entries, then run a separate M5-only comparison later.

Should we simulate WATCHLIST trades or only ELIGIBLE trades?

Answer: **Simulate WATCHLIST for now.** Eligible signals may be rare, and WATCHLIST paper simulation helps determine whether the scoring rules are too strict. Keep them clearly marked as `WATCHLIST_SIGNAL`.

Should we keep XAUUSDm enabled if spread is often bad?

Answer: **Yes for monitoring, no for forced trading.** Keep it enabled so the bot records when it is blocked by spread. Do not loosen spread logic yet.

What minimum clean paper sample is needed before strategy improvement?

Answer: **At least 20 clean paper trades**, with a better target of 30-50. The sample should include symbol, timeframe, signal status, spread, volatility, and close outcome.

What should be the next logical stage after clean paper testing?

Answer: **Paper performance review and rule calibration**, not live execution. The next stage should analyze clean paper results to decide whether M1 should remain enabled, whether WATCHLIST is too weak, and whether scoring/cost filters need adjustment.

## 9. Final Recommendation

Continue development?

Answer: **Yes, after clean paper testing begins.**

Start clean paper testing?

Answer: **Yes.** The active paper log files are currently absent, meaning the archived pre-9.2 data is out of the active paper state.

Fix anything else first?

Answer: **No critical code fix is required before clean paper testing.** The main operational blocker is MT5 connectivity if IPC timeout appears.

What should not be done yet?

- Do not add live trading.
- Do not call `mt5.order_send`.
- Do not add broker execution.
- Do not optimize thresholds from pre-9.2 paper data.
- Do not disable M1 or XAUUSDm until clean paper results justify it.
- Do not add AI/ML, SMC, Telegram, dashboard, or backtesting yet.

## Readiness Decision

Final classification:
- Foundation: **PASS**
- Data collection: **PASS**
- Market analysis: **PASS**
- Signal scoring: **PASS / NEEDS MORE DATA**
- Decision journal: **PASS**
- Outcome tracking: **PASS / NEEDS MORE DATA**
- Trade planning: **PASS**
- Broker/cost validation: **PASS**
- Paper execution: **PASS after Stage 9.2**
- Paper status reporting: **PASS**
- Paper timing reliability: **PASS**
- Strategy quality: **NEEDS MORE DATA**
- Real execution readiness: **FAIL by design, not implemented yet**

Recommended next action: start fresh paper testing and collect a clean Stage 9.2+ sample before changing strategy logic.
