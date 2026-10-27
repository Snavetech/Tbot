"""
Comprehensive Quantitative Performance Metrics
Calculates financial, statistical, and risk metrics with safe zero-division
and edge-case handling for simulated Forex backtests.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import math
import numpy as np


class PerformanceMetricsCalculator:
    """
    Computes institutional performance metrics from trade logs and equity curves.
    """

    @classmethod
    def calculate(
        cls,
        initial_balance: float,
        trades: List[Dict[str, Any]],
        equity_curve: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculates all performance metrics. Safe against zero-trade and zero-loss scenarios.
        """
        total_trades = len(trades)

        if total_trades == 0:
            return cls._empty_metrics(initial_balance)

        winning_trades = [t for t in trades if t["net_pnl"] > 0]
        losing_trades = [t for t in trades if t["net_pnl"] < 0]
        breakeven_trades = [t for t in trades if t["net_pnl"] == 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = round((win_count / total_trades * 100.0), 2)

        gross_profit = round(sum(t["net_pnl"] for t in winning_trades), 2)
        gross_loss = round(abs(sum(t["net_pnl"] for t in losing_trades)), 2)

        # Profit Factor handling
        if gross_loss > 0:
            profit_factor = round(gross_profit / gross_loss, 2)
        elif gross_profit > 0:
            profit_factor = 99.0  # Undefined high (no losses)
        else:
            profit_factor = 0.0

        net_pnl = round(sum(t["net_pnl"] for t in trades), 2)
        final_balance = round(initial_balance + net_pnl, 2)
        return_pct = round((net_pnl / initial_balance * 100.0), 2) if initial_balance > 0 else 0.0

        avg_win = round(gross_profit / win_count, 2) if win_count > 0 else 0.0
        avg_loss = round(gross_loss / loss_count, 2) if loss_count > 0 else 0.0
        win_loss_ratio = round(avg_win / avg_loss, 2) if avg_loss > 0 else 0.0

        # Expectancy: (WinRate * AvgWin) - (LossRate * AvgLoss)
        win_prob = win_count / total_trades
        loss_prob = loss_count / total_trades
        expectancy_dollars = round((win_prob * avg_win) - (loss_prob * avg_loss), 2)
        expectancy_r = round(expectancy_dollars / avg_loss, 2) if avg_loss > 0 else (1.0 if expectancy_dollars > 0 else 0.0)

        # Drawdowns from equity curve
        max_dd_pct = 0.0
        max_dd_amount = 0.0
        if equity_curve:
            peak = initial_balance
            for pt in equity_curve:
                eq = pt["equity"]
                if eq > peak:
                    peak = eq
                dd_amt = peak - eq
                dd_pct = (dd_amt / peak * 100.0) if peak > 0 else 0.0
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct
                if dd_amt > max_dd_amount:
                    max_dd_amount = dd_amt

        # Holding duration
        holding_seconds_list = [t.get("holding_seconds", 0) for t in trades]
        avg_holding_seconds = int(np.mean(holding_seconds_list)) if holding_seconds_list else 0
        avg_holding_hours = round(avg_holding_seconds / 3600.0, 1)

        holding_bars_list = [t.get("holding_bars", 0) for t in trades]
        avg_holding_bars = round(float(np.mean(holding_bars_list)), 1) if holding_bars_list else 0.0

        # Cost Breakdown
        total_commission = round(sum(t.get("commission", 0.0) for t in trades), 2)
        total_swap = round(sum(t.get("swap", 0.0) for t in trades), 2)

        # Performance by Year
        performance_by_year: Dict[str, Dict[str, Any]] = {}
        for t in trades:
            entry_ts = t.get("entry_time", 0)
            if entry_ts > 0:
                year_str = str(datetime.fromtimestamp(entry_ts, tz=timezone.utc).year)
            else:
                year_str = "Unknown"

            if year_str not in performance_by_year:
                performance_by_year[year_str] = {
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "net_pnl": 0.0
                }
            performance_by_year[year_str]["trades"] += 1
            if t["net_pnl"] > 0:
                performance_by_year[year_str]["wins"] += 1
            elif t["net_pnl"] < 0:
                performance_by_year[year_str]["losses"] += 1
            performance_by_year[year_str]["net_pnl"] = round(
                performance_by_year[year_str]["net_pnl"] + t["net_pnl"], 2
            )

        for y, ydata in performance_by_year.items():
            y_trades = ydata["trades"]
            ydata["win_rate"] = round((ydata["wins"] / y_trades * 100.0), 1) if y_trades > 0 else 0.0

        # Performance by Exit Reason
        performance_by_exit: Dict[str, Dict[str, Any]] = {}
        for t in trades:
            reason = t.get("exit_reason", "UNKNOWN")
            if reason not in performance_by_exit:
                performance_by_exit[reason] = {"count": 0, "net_pnl": 0.0}
            performance_by_exit[reason]["count"] += 1
            performance_by_exit[reason]["net_pnl"] = round(
                performance_by_exit[reason]["net_pnl"] + t["net_pnl"], 2
            )

        return {
            "initial_balance": initial_balance,
            "final_balance": final_balance,
            "net_pnl": net_pnl,
            "return_pct": return_pct,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "profit_factor": profit_factor,
            "total_trades": total_trades,
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "breakeven_trades": len(breakeven_trades),
            "win_rate": win_rate,
            "average_win": avg_win,
            "average_loss": avg_loss,
            "win_loss_ratio": win_loss_ratio,
            "trade_expectancy": expectancy_dollars,
            "trade_expectancy_r": expectancy_r,
            "max_drawdown_amount": round(max_dd_amount, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "average_holding_bars": avg_holding_bars,
            "average_holding_hours": avg_holding_hours,
            "total_commission": total_commission,
            "total_swap": total_swap,
            "performance_by_year": performance_by_year,
            "performance_by_exit_reason": performance_by_exit,
        }

    @classmethod
    def _empty_metrics(cls, initial_balance: float) -> Dict[str, Any]:
        """Safe default metric dictionary for backtests with 0 trades."""
        return {
            "initial_balance": initial_balance,
            "final_balance": initial_balance,
            "net_pnl": 0.0,
            "return_pct": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "profit_factor": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "breakeven_trades": 0,
            "win_rate": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "win_loss_ratio": 0.0,
            "trade_expectancy": 0.0,
            "trade_expectancy_r": 0.0,
            "max_drawdown_amount": 0.0,
            "max_drawdown_pct": 0.0,
            "average_holding_bars": 0.0,
            "average_holding_hours": 0.0,
            "total_commission": 0.0,
            "total_swap": 0.0,
            "performance_by_year": {},
            "performance_by_exit_reason": {},
        }
