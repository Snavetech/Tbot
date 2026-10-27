"""
Report Metrics Generator
Compiles performance analytics from persisted database records.
Never fabricates results on days without trades.
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.models import TradeRecord, AccountSnapshot, PositionRecord
from backend.app.schemas.reports import PerformanceMetrics, ReportSummaryResponse, EquityPoint


class ReportGenerator:
    """Calculates verifiable performance statistics from stored database records"""

    @staticmethod
    def get_period_dates(period_type: str) -> Tuple[datetime, datetime]:
        now = datetime.now(timezone.utc)
        if period_type == "daily":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period_type == "weekly":
            start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        elif period_type == "monthly":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # all_time
            start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        return start, now

    @staticmethod
    def generate_report_summary(
        db: Session,
        period_type: str = "all_time",
        current_equity: float = 10000.0,
        current_balance: float = 10000.0
    ) -> ReportSummaryResponse:
        start_date, end_date = ReportGenerator.get_period_dates(period_type)

        trades: List[TradeRecord] = db.query(TradeRecord).filter(
            TradeRecord.close_time >= start_date,
            TradeRecord.close_time <= end_date
        ).order_by(TradeRecord.close_time.asc()).all()

        total_trades = len(trades)
        winning_trades = [t for t in trades if t.net_pnl > 0]
        losing_trades = [t for t in trades if t.net_pnl < 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = round((win_count / total_trades * 100.0), 2) if total_trades > 0 else 0.0

        gross_profit = round(sum(t.net_pnl for t in winning_trades), 2)
        gross_loss = round(abs(sum(t.net_pnl for t in losing_trades)), 2)
        net_pnl = round(sum(t.net_pnl for t in trades), 2)

        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

        total_commission = round(sum(t.commission for t in trades), 2)
        total_swap = round(sum(t.swap for t in trades), 2)

        avg_win = round(gross_profit / win_count, 2) if win_count > 0 else 0.0
        avg_loss = round(gross_loss / loss_count, 2) if loss_count > 0 else 0.0
        expectancy = round(((win_rate / 100.0) * avg_win) - (((100.0 - win_rate) / 100.0) * avg_loss), 2)

        # Performance by strategy breakdown
        perf_by_strategy: Dict[str, Any] = {}
        perf_by_regime: Dict[str, Any] = {}

        for t in trades:
            strat = t.strategy_used or "unknown"
            if strat not in perf_by_strategy:
                perf_by_strategy[strat] = {"trades": 0, "net_pnl": 0.0, "wins": 0}
            perf_by_strategy[strat]["trades"] += 1
            perf_by_strategy[strat]["net_pnl"] = round(perf_by_strategy[strat]["net_pnl"] + t.net_pnl, 2)
            if t.net_pnl > 0:
                perf_by_strategy[strat]["wins"] += 1

            reg = t.market_regime or "unknown"
            if reg not in perf_by_regime:
                perf_by_regime[reg] = {"trades": 0, "net_pnl": 0.0, "wins": 0}
            perf_by_regime[reg]["trades"] += 1
            perf_by_regime[reg]["net_pnl"] = round(perf_by_regime[reg]["net_pnl"] + t.net_pnl, 2)
            if t.net_pnl > 0:
                perf_by_regime[reg]["wins"] += 1

        # Calculate equity curve and max drawdown from trade sequence
        starting_balance = round(current_balance - net_pnl, 2)
        running_equity = starting_balance
        peak_equity = starting_balance
        max_drawdown = 0.0
        max_drawdown_pct = 0.0

        equity_points = [
            EquityPoint(
                timestamp=start_date.isoformat(),
                equity=starting_balance,
                balance=starting_balance,
                drawdown_pct=0.0
            )
        ]

        for t in trades:
            running_equity = round(running_equity + t.net_pnl, 2)
            peak_equity = max(peak_equity, running_equity)
            dd = peak_equity - running_equity
            dd_pct = (dd / peak_equity * 100.0) if peak_equity > 0 else 0.0

            if dd > max_drawdown:
                max_drawdown = dd
                max_drawdown_pct = dd_pct

            equity_points.append(
                EquityPoint(
                    timestamp=t.close_time.isoformat(),
                    equity=running_equity,
                    balance=running_equity,
                    drawdown_pct=round(dd_pct, 2)
                )
            )

        # Append current point
        if not trades:
            equity_points.append(
                EquityPoint(
                    timestamp=end_date.isoformat(),
                    equity=current_equity,
                    balance=current_balance,
                    drawdown_pct=0.0
                )
            )

        metrics = PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate=win_rate,
            profit_factor=profit_factor,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_pnl=net_pnl,
            total_commission=total_commission,
            total_swap=total_swap,
            average_win=avg_win,
            average_loss=avg_loss,
            trade_expectancy=expectancy,
            max_drawdown_amount=round(max_drawdown, 2),
            max_drawdown_pct=round(max_drawdown_pct, 2),
            performance_by_strategy=perf_by_strategy,
            performance_by_regime=perf_by_regime
        )

        trade_dicts = [
            {
                "id": t.id,
                "ticket": t.ticket,
                "symbol": t.symbol,
                "type": t.trade_type,
                "volume": t.volume,
                "open_price": t.open_price,
                "close_price": t.close_price,
                "open_time": t.open_time.isoformat(),
                "close_time": t.close_time.isoformat(),
                "net_pnl": t.net_pnl,
                "exit_reason": t.exit_reason,
                "strategy": t.strategy_used,
            }
            for t in trades
        ]

        data_limitations = [
            "All figures are derived directly from persisted demo database records.",
            "Trading is strictly restricted to verified Demo accounts.",
            "Past performance does not guarantee future results."
        ]
        if total_trades == 0:
            data_limitations.append("No closed trades recorded in this reporting period.")

        return ReportSummaryResponse(
            period_type=period_type,
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
            timezone="UTC",
            starting_balance=starting_balance,
            ending_balance=current_balance,
            starting_equity=starting_balance,
            ending_equity=current_equity,
            metrics=metrics,
            equity_curve=equity_points,
            trades=trade_dicts,
            data_limitations=data_limitations
        )
