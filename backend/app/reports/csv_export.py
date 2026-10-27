"""
CSV Export Utility for trades and metrics
"""
import csv
from pathlib import Path
from typing import List, Dict, Any
from backend.app.schemas.reports import ReportSummaryResponse


class CSVReportExporter:
    """Exports structured trade data and summary metrics to CSV files"""

    @staticmethod
    def export_trades_csv(trades: List[Dict[str, Any]], output_path: str) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "id", "ticket", "symbol", "type", "volume",
            "open_price", "close_price", "open_time", "close_time",
            "net_pnl", "exit_reason", "strategy"
        ]

        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for t in trades:
                writer.writerow(t)

        return output_path

    @staticmethod
    def export_metrics_csv(report: ReportSummaryResponse, output_path: str) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        m = report.metrics
        rows = [
            ("Period Type", report.period_type),
            ("Period Start", report.period_start),
            ("Period End", report.period_end),
            ("Starting Balance", report.starting_balance),
            ("Ending Balance", report.ending_balance),
            ("Starting Equity", report.starting_equity),
            ("Ending Equity", report.ending_equity),
            ("Total Trades", m.total_trades),
            ("Winning Trades", m.winning_trades),
            ("Losing Trades", m.losing_trades),
            ("Win Rate (%)", m.win_rate),
            ("Profit Factor", m.profit_factor),
            ("Gross Profit ($)", m.gross_profit),
            ("Gross Loss ($)", m.gross_loss),
            ("Net P&L ($)", m.net_pnl),
            ("Total Commission ($)", m.total_commission),
            ("Total Swap ($)", m.total_swap),
            ("Average Win ($)", m.average_win),
            ("Average Loss ($)", m.average_loss),
            ("Trade Expectancy ($)", m.trade_expectancy),
            ("Max Drawdown (%)", m.max_drawdown_pct),
        ]

        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value"])
            for k, v in rows:
                writer.writerow([k, v])

        return output_path
