"""
Offline Research Reporting & Export Subsystem
Generates audit-ready PDF research reports via ReportLab and exports CSV/JSON trade records.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone
import io
import csv

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


class BacktestReportGenerator:
    """
    Builds research reports for offline backtests.
    """

    @classmethod
    def generate_pdf(
        cls,
        results: Dict[str, Any],
        data_quality: Optional[Dict[str, Any]],
        output_path: str
    ) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "RTitle",
            parent=styles["Heading1"],
            fontSize=20,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "RSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=12,
        )
        section_style = ParagraphStyle(
            "RSection",
            parent=styles["Heading2"],
            fontSize=12,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=10,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "RBody",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#334155"),
        )
        alert_style = ParagraphStyle(
            "RAlert",
            parent=styles["Normal"],
            fontSize=7.5,
            textColor=colors.HexColor("#991b1b"),
            leading=10,
        )

        elements = []

        # 1. Title Banner
        elements.append(Paragraph("TradePilot AI — Quantitative Research & Backtest Report", title_style))
        elements.append(Paragraph(
            f"EUR/USD Offline Historical Strategy Evaluation | Mode: OFFLINE SIMULATION (Zero Live Order Execution) | "
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            subtitle_style
        ))
        elements.append(Spacer(1, 8))

        # 2. Prominent Research Disclaimer
        disclaimer_box = [
            ["RESEARCH COMPLIANCE NOTICE: This report represents simulated historical research. "
             "Simulated trading has inherent limitations: it does not reflect live market liquidity, actual order queue priority, "
             "or unpredictable slippage during major macroeconomic news releases. Past performance does not guarantee future results."]
        ]
        disc_table = Table(disclaimer_box, colWidths=[540])
        disc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#991b1b")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#fca5a5")),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(disc_table)
        elements.append(Spacer(1, 10))

        # 3. Data Ingestion Diagnostics
        if data_quality:
            elements.append(Paragraph("Dataset & Quality Audit", section_style))
            dq_rows = [
                ["Source File", str(data_quality.get("source_name", "N/A")), "Cadence", f"{data_quality.get('cadence_seconds', 0)}s"],
                ["Total Rows", str(data_quality.get("total_rows", 0)), "Valid Rows", str(data_quality.get("valid_rows", 0))],
                ["Start Time", str(data_quality.get("start_time_utc", "N/A")), "End Time", str(data_quality.get("end_time_utc", "N/A"))],
                ["Duplicate Bars", str(data_quality.get("duplicate_timestamps", 0)), "Gaps Detected", str(data_quality.get("detected_gaps", 0))],
                ["Historical Spread", "YES" if data_quality.get("has_historical_spread") else f"NO (Assumed {data_quality.get('assumed_spread_pips', 1.2)} pips)", "Rejected Rows", str(data_quality.get("rejected_rows", 0))],
            ]
            dq_table = Table(dq_rows, colWidths=[120, 150, 120, 150])
            dq_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ]))
            elements.append(dq_table)
            elements.append(Spacer(1, 10))

        # 4. Strategy & Cost Assumptions Table
        elements.append(Paragraph("Parameters & Modeled Costs", section_style))
        strat_cfg = results.get("strategy_config", {})
        cost_cfg = results.get("cost_scenario", {})
        risk_cfg = results.get("risk_config", {})

        param_rows = [
            ["Parameter", "Setting", "Cost / Risk Assumption", "Setting"],
            ["Fast EMA", f"{strat_cfg.get('fast_ema_period', 50)} periods", "Cost Scenario", str(cost_cfg.get("scenario_name", "Normal"))],
            ["Slow EMA", f"{strat_cfg.get('slow_ema_period', 200)} periods", "Default Spread", f"{cost_cfg.get('default_spread_pips', 1.2)} pips"],
            ["RSI Thresholds", f"Long: {strat_cfg.get('rsi_long_min', 52)}-{strat_cfg.get('rsi_long_max', 68)}", "Commission / Lot", f"${cost_cfg.get('commission_per_lot_round_turn', 7.0):.2f}"],
            ["ATR Stop Mult", f"{strat_cfg.get('atr_stop_multiplier', 1.5)}x ATR", "Slippage Modeled", f"{cost_cfg.get('slippage_pips', 0.5)} pips"],
            ["Risk:Reward", f"1 : {strat_cfg.get('risk_reward_ratio', 2.0)}", "Risk Per Trade", f"{risk_cfg.get('risk_per_trade_pct', 0.25)}% equity"],
            ["Cooldown", f"{strat_cfg.get('cooldown_bars', 2)} bars", "Daily Loss Limit", f"{risk_cfg.get('max_daily_loss_pct', 1.0)}%"],
        ]
        param_table = Table(param_rows, colWidths=[120, 150, 130, 140])
        param_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f1f5f9")),
        ]))
        elements.append(param_table)
        elements.append(Spacer(1, 10))

        # 5. Core Performance Metrics Table
        full_metrics = results.get("full_dataset", {}).get("metrics") or results.get("metrics", {})
        net_pnl = full_metrics.get("net_pnl", 0.0)
        pnl_color = "#16a34a" if net_pnl >= 0 else "#dc2626"
        pnl_prefix = "+" if net_pnl >= 0 else ""

        elements.append(Paragraph("Overall Performance Summary", section_style))
        summary_rows = [
            ["Metric", "Value", "Metric", "Value"],
            ["Net Profit/Loss", f"{pnl_prefix}${net_pnl:,.2f}", "Total Trades", str(full_metrics.get("total_trades", 0))],
            ["Return on Capital", f"{full_metrics.get('return_pct', 0.0)}%", "Win Rate", f"{full_metrics.get('win_rate', 0.0)}%"],
            ["Profit Factor", str(full_metrics.get("profit_factor", 0.0)), "Winning / Losing", f"{full_metrics.get('winning_trades', 0)}W / {full_metrics.get('losing_trades', 0)}L"],
            ["Average Win", f"${full_metrics.get('average_win', 0.0):,.2f}", "Average Loss", f"${full_metrics.get('average_loss', 0.0):,.2f}"],
            ["Trade Expectancy", f"${full_metrics.get('trade_expectancy', 0.0):,.2f}", "Max Drawdown", f"{full_metrics.get('max_drawdown_pct', 0.0)}% (${full_metrics.get('max_drawdown_amount', 0.0):,.2f})"],
            ["Avg Holding Duration", f"{full_metrics.get('average_holding_hours', 0.0)} hrs", "Total Commission", f"${full_metrics.get('total_commission', 0.0):,.2f}"],
        ]
        sum_table = Table(summary_rows, colWidths=[130, 140, 130, 140])
        sum_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
            ("TEXTCOLOR", (1, 1), (1, 1), colors.HexColor(pnl_color)),
            ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold"),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ]))
        elements.append(sum_table)
        elements.append(Spacer(1, 10))

        # 6. Chronological Partition Breakdown (Dev vs Val vs Test)
        partitions = results.get("partitions")
        if partitions:
            elements.append(Paragraph("Chronological Data Partition Analysis", section_style))
            part_rows = [
                ["Partition", "Date Range", "Trades", "Win Rate", "Profit Factor", "Net P&L", "Max DD"]
            ]
            for pkey, pdata in partitions.items():
                pm = pdata.get("metrics", {})
                p_pnl = pm.get("net_pnl", 0.0)
                p_prefix = "+" if p_pnl >= 0 else ""
                part_rows.append([
                    pdata.get("label", pkey),
                    f"{pdata.get('bars_count', 0)} bars",
                    str(pm.get("total_trades", 0)),
                    f"{pm.get('win_rate', 0.0)}%",
                    str(pm.get("profit_factor", 0.0)),
                    f"{p_prefix}${p_pnl:,.2f}",
                    f"{pm.get('max_drawdown_pct', 0.0)}%",
                ])

            part_table = Table(part_rows, colWidths=[150, 70, 50, 60, 70, 75, 65])
            part_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ]))
            elements.append(part_table)
            elements.append(Spacer(1, 10))

        # 7. Sample Trade Log (Last 20 trades)
        trades = results.get("trades") or results.get("full_dataset", {}).get("trades", [])
        if trades:
            elements.append(Paragraph("Trade Execution Audit Trail (Sample)", section_style))
            t_rows = [["ID", "Type", "Vol", "Entry Price", "Exit Price", "Net P&L", "Exit Reason", "MFE/MAE"]]
            for t in trades[-20:]:
                t_pnl = t.get("net_pnl", 0.0)
                pnl_str = f"+${t_pnl:.2f}" if t_pnl >= 0 else f"-${abs(t_pnl):.2f}"
                t_rows.append([
                    str(t.get("trade_id", "")),
                    t.get("type", ""),
                    f"{t.get('volume', 0.0):.2f}",
                    f"{t.get('entry_price', 0.0):.5f}",
                    f"{t.get('exit_price', 0.0):.5f}",
                    pnl_str,
                    t.get("exit_reason", ""),
                    f"{t.get('mfe_pips', 0.0)}/{t.get('mae_pips', 0.0)}p",
                ])

            t_table = Table(t_rows, colWidths=[30, 40, 35, 75, 75, 65, 120, 100])
            t_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#475569")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]))
            elements.append(t_table)

        doc.build(elements)
        return output_path

    @classmethod
    def export_csv_trades(cls, trades: List[Dict[str, Any]]) -> str:
        """Generates CSV string from trade records."""
        output = io.StringIO()
        fieldnames = [
            "trade_id", "type", "volume", "entry_time", "exit_time",
            "entry_price", "exit_price", "sl", "tp", "gross_pnl",
            "commission", "swap", "net_pnl", "exit_reason",
            "holding_bars", "holding_seconds", "mfe_pips", "mae_pips"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for t in trades:
            writer.writerow(t)
        return output.getvalue()
