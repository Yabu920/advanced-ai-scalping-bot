"""Paper execution engine for simulation-only trade handling."""

from __future__ import annotations

from typing import Any

import pandas as pd

from paper.paper_filters import paper_filter_summary, paper_trade_allowed_by_filters
from paper.paper_trade import CLOSED_SL, CLOSED_TP, OPEN, build_paper_trade_from_plan


class PaperExecutionEngine:
    """Create and update paper trades without interacting with MT5 orders."""

    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self.last_candidate_decisions: list[dict[str, Any]] = []

    def should_create_paper_trade(
        self,
        plan: dict,
        validation: dict | None,
        open_trades: list[dict],
    ) -> dict[str, Any]:
        validation = validation or {}
        if not self.settings.paper_trading_enabled:
            return {"allowed": False, "reason": "Paper trading is disabled."}
        if not plan or not plan.get("valid"):
            return {"allowed": False, "reason": "Plan is missing or invalid."}
        if plan.get("signal_status") == "REJECTED":
            return {"allowed": False, "reason": "Rejected signals are never paper simulated."}

        # Apply experiment admission before any paper-trade construction or
        # simulation bookkeeping. In particular, a SELL-only run cannot create
        # a BUY trade.
        filters_allowed, filter_reasons = paper_trade_allowed_by_filters(
            {"plan": plan, "validation": validation},
            self.settings,
        )
        if not filters_allowed:
            return {"allowed": False, "reason": "; ".join(filter_reasons), "filter_reasons": filter_reasons}

        symbol = plan.get("symbol")
        timeframe = plan.get("timeframe")
        if any(trade.get("status") == OPEN and trade.get("symbol") == symbol and trade.get("timeframe") == timeframe for trade in open_trades):
            return {"allowed": False, "reason": "Duplicate open paper trade for symbol/timeframe."}
        if len([trade for trade in open_trades if trade.get("status") == OPEN]) >= self.settings.paper_max_open_trades:
            return {"allowed": False, "reason": "Maximum open paper trades reached."}
        if len([trade for trade in open_trades if trade.get("status") == OPEN and trade.get("symbol") == symbol]) >= self.settings.paper_max_open_trades_per_symbol:
            return {"allowed": False, "reason": "Maximum open paper trades per symbol reached."}

        status = plan.get("signal_status")
        if status == "WATCHLIST":
            if self.settings.paper_trade_eligible_only:
                return {"allowed": False, "reason": "Paper simulation is restricted to ELIGIBLE signals."}
            if not self.settings.paper_include_watchlist:
                return {"allowed": False, "reason": "WATCHLIST paper simulation is disabled."}
            if self.settings.paper_use_pre_execution_validation and not (
                validation.get("plan_valid")
                and validation.get("broker_constraints_valid")
                and validation.get("costs_valid")
            ):
                return {"allowed": False, "reason": "WATCHLIST plan failed pre-execution validation."}
            normal_reason = "WATCHLIST plan allowed for preview paper simulation."

        elif status == "ELIGIBLE":
            if self.settings.paper_use_pre_execution_validation and not validation.get("execution_ready_later"):
                return {"allowed": False, "reason": "ELIGIBLE plan is not execution-ready-later after validation."}
            normal_reason = "ELIGIBLE plan allowed for paper simulation."

        else:
            return {"allowed": False, "reason": "Signal status is not supported for paper simulation."}

        return {"allowed": True, "reason": normal_reason, "filter_reasons": []}

    def create_paper_trades_from_plans(
        self,
        plans: dict,
        validations: dict,
        existing_open_trades: list[dict],
    ) -> list[dict]:
        new_trades: list[dict] = []
        open_pool = list(existing_open_trades)
        self.last_candidate_decisions = []
        for symbol, symbol_plans in plans.items():
            for timeframe, plan in symbol_plans.items():
                validation = validations.get(symbol, {}).get(timeframe, {})
                decision = self.should_create_paper_trade(plan, validation, open_pool)
                self.last_candidate_decisions.append(
                    {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "direction": plan.get("direction"),
                        "signal_status": plan.get("signal_status"),
                        "signal_score": plan.get("signal_score"),
                        "allowed": decision["allowed"],
                        "reason": decision["reason"],
                        "filtered_by_paper_filters": bool(decision.get("filter_reasons")),
                        "paper_filter_reasons": decision.get("filter_reasons", []),
                    }
                )
                if not decision["allowed"]:
                    continue
                enriched_plan = {
                    **plan,
                    "paper_experiment_name": getattr(self.settings, "paper_experiment_name", "baseline") or "baseline",
                    "paper_filters_enabled": bool(getattr(self.settings, "paper_filters_enabled", False)),
                    "paper_filter_summary": paper_filter_summary(self.settings),
                }
                trade = build_paper_trade_from_plan(enriched_plan, validation)
                trade["open_reason"] = decision["reason"]
                new_trades.append(trade)
                open_pool.append(trade)
        return new_trades

    @staticmethod
    def _to_timestamp(value: Any) -> pd.Timestamp | None:
        if value is None:
            return None
        try:
            timestamp = pd.Timestamp(value)
        except (TypeError, ValueError):
            return None
        if pd.isna(timestamp):
            return None
        if timestamp.tzinfo is not None:
            timestamp = timestamp.tz_convert("UTC").tz_localize(None)
        return timestamp

    @staticmethod
    def _to_iso(value: Any) -> str | None:
        timestamp = PaperExecutionEngine._to_timestamp(value)
        if timestamp is not None:
            return timestamp.isoformat()
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _append_issue(self, trade: dict, issue: str) -> dict:
        updated = dict(trade)
        issues = list(updated.get("issues") or [])
        if issue not in issues:
            issues.append(issue)
        updated["issues"] = issues
        return updated

    def get_closed_candles_after_time(self, df: pd.DataFrame, after_time: Any) -> list[dict]:
        if df.empty or "time" not in df.columns:
            return []

        candles = df.copy()
        if "is_closed_candle" in candles.columns:
            candles = candles[candles["is_closed_candle"] == True]
        elif len(candles) > 1:
            candles = candles.iloc[:-1]
        else:
            return []

        after_timestamp = self._to_timestamp(after_time)
        candles["time"] = pd.to_datetime(candles["time"], errors="coerce")
        candles = candles.dropna(subset=["time"]).sort_values("time")
        if after_timestamp is not None:
            candle_times = candles["time"]
            if getattr(candle_times.dt, "tz", None) is not None:
                candle_times = candle_times.dt.tz_convert("UTC").dt.tz_localize(None)
            candles = candles[candle_times > after_timestamp]
        return candles.to_dict("records")

    def update_open_trade_with_candles(self, trade: dict, candles: list[dict]) -> dict:
        if trade.get("status") != OPEN:
            return trade

        opened_time = self._to_timestamp(
            trade.get("opened_candle_time")
            or trade.get("signal_candle_time")
            or trade.get("created_time_utc")
        )
        last_evaluated_time = self._to_timestamp(trade.get("last_evaluated_candle_time")) or opened_time
        updated_trade = dict(trade)
        issues = list(updated_trade.get("issues") or [])
        updated_trade["issues"] = issues

        def sort_key(candle: dict) -> pd.Timestamp:
            return self._to_timestamp(candle.get("time")) or pd.Timestamp.max

        for candle in sorted(candles, key=sort_key):
            raw_candle_time = candle.get("time")
            candle_time = self._to_timestamp(candle.get("time"))
            if candle_time is None and any([opened_time, last_evaluated_time]):
                continue
            if candle_time is not None and opened_time is not None and candle_time <= opened_time:
                continue
            if candle_time is not None and last_evaluated_time is not None and candle_time <= last_evaluated_time:
                continue

            if candle_time is not None:
                updated_trade["last_evaluated_candle_time"] = candle_time.isoformat()
                last_evaluated_time = candle_time

            high = float(candle.get("high"))
            low = float(candle.get("low"))
            direction = updated_trade.get("direction")
            stop_loss = float(updated_trade.get("stop_loss"))
            take_profit = float(updated_trade.get("take_profit"))

            if direction == "BUY":
                sl_hit = low <= stop_loss
                tp_hit = high >= take_profit
            elif direction == "SELL":
                sl_hit = high >= stop_loss
                tp_hit = low <= take_profit
            else:
                return updated_trade

            close_status = None
            close_price = None
            close_reason = None
            if sl_hit and tp_hit:
                close_status = CLOSED_SL
                close_price = stop_loss
                close_reason = "Both TP and SL touched in same candle; conservative SL-first assumption."
            elif sl_hit:
                close_status = CLOSED_SL
                close_price = stop_loss
                close_reason = "Stop loss hit in paper simulation."
            elif tp_hit:
                close_status = CLOSED_TP
                close_price = take_profit
                close_reason = "Take profit hit in paper simulation."

            if not close_status:
                continue

            if candle_time is not None and opened_time is not None and candle_time <= opened_time:
                issues.append("Invalid paper close time before or equal to opened candle time.")
                continue

            updated_trade["status"] = close_status
            updated_trade["close_time_utc"] = candle_time.isoformat() if candle_time is not None else str(raw_candle_time)
            updated_trade["close_price"] = close_price
            if close_status == CLOSED_TP:
                gross_pnl_amount = float(updated_trade.get("risk_amount", 0)) * float(updated_trade.get("rr_ratio", 0))
                gross_pnl_r = float(updated_trade.get("rr_ratio", 0))
            else:
                gross_pnl_amount = -float(updated_trade.get("risk_amount", 0))
                gross_pnl_r = -1.0

            updated_trade["gross_pnl_amount"] = gross_pnl_amount
            updated_trade["gross_pnl_r"] = gross_pnl_r
            spread_cost = updated_trade.get("spread_cost_amount")
            spread_cost_known = updated_trade.get("spread_cost_known") is True
            if spread_cost_known and spread_cost is not None:
                total_cost_amount = max(float(spread_cost), 0.0)
                risk_amount = float(updated_trade.get("risk_amount", 0))
                updated_trade["total_cost_amount"] = total_cost_amount
                updated_trade["pnl_amount"] = gross_pnl_amount - total_cost_amount
                updated_trade["pnl_r"] = (
                    updated_trade["pnl_amount"] / risk_amount if risk_amount > 0 else gross_pnl_r
                )
                updated_trade["pnl_basis"] = "NET_AFTER_SPREAD"
            else:
                updated_trade["total_cost_amount"] = None
                updated_trade["pnl_amount"] = gross_pnl_amount
                updated_trade["pnl_r"] = gross_pnl_r
                updated_trade["pnl_basis"] = "GROSS_SPREAD_UNKNOWN"
                if "Spread cost unavailable; reported PnL is gross." not in issues:
                    issues.append("Spread cost unavailable; reported PnL is gross.")
            updated_trade["close_reason"] = close_reason
            return updated_trade

        return updated_trade

    def update_open_trade_with_candle(self, trade: dict, latest_closed_candle: dict) -> dict:
        return self.update_open_trade_with_candles(trade, [latest_closed_candle])

    def recover_open_trade_if_latest_candle_breached(self, trade: dict, latest_closed_candle: dict | None) -> dict:
        if trade.get("status") != OPEN or latest_closed_candle is None:
            return trade
        candle_time = self._to_timestamp(latest_closed_candle.get("time"))
        opened_time = self._to_timestamp(
            trade.get("opened_candle_time")
            or trade.get("signal_candle_time")
            or trade.get("created_time_utc")
        )
        if candle_time is None or (opened_time is not None and candle_time <= opened_time):
            return trade

        recovered = self.update_open_trade_with_candles(
            {**trade, "last_evaluated_candle_time": None},
            [latest_closed_candle],
        )
        if recovered.get("status") != OPEN:
            return self._append_issue(recovered, "Recovered close from latest closed candle breach after previous evaluation skip.")
        return trade

    def get_latest_closed_candle(self, df: pd.DataFrame) -> dict | None:
        if df.empty:
            return None
        if "is_closed_candle" in df.columns:
            closed = df[df["is_closed_candle"] == True]
            if closed.empty:
                return None
            return closed.iloc[-1].to_dict()
        if len(df) < 2:
            return None
        return df.iloc[-2].to_dict()

    def update_open_trades(
        self,
        open_trades: list[dict],
        market_data: dict[str, dict[str, pd.DataFrame]],
    ) -> list[dict]:
        updated: list[dict] = []
        for trade in open_trades:
            df = market_data.get(trade.get("symbol"), {}).get(trade.get("timeframe"))
            if df is None:
                updated.append(trade)
                continue
            after_time = trade.get("last_evaluated_candle_time") or trade.get("opened_candle_time")
            latest = self.get_latest_closed_candle(df)
            latest_time = self._to_timestamp(latest.get("time")) if latest else None
            last_evaluated_time = self._to_timestamp(trade.get("last_evaluated_candle_time"))
            if latest_time is not None and last_evaluated_time is not None and last_evaluated_time > latest_time:
                updated.append(self._append_issue(trade, "last_evaluated_candle_time is ahead of latest closed candle."))
                continue
            candles = self.get_closed_candles_after_time(df, after_time)
            result = self.update_open_trade_with_candles(trade, candles) if candles else trade
            if result.get("status") == OPEN:
                result = self.recover_open_trade_if_latest_candle_breached(result, latest)
            updated.append(result)
        return updated
