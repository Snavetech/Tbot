"""
PDF Report Generator using ReportLab
Generates audit-ready performance reports with tables, metrics, and compliance notices.
"""
from pathlib import Path
from datetime import datetime, timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from backend.app.schemas.reports import ReportSummaryResponse


class PDFReportExporter:
    """Builds formatted PDF reports from verified report summaries"""

    @staticmethod
    def generate_pdf(report: ReportSummaryResponse, output_path: str) -> str:
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

        # Custom Styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=22,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=11,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=14,
        )
        section_style = ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=12,
            spaceAfter=8,
        )
        normal_style = ParagraphStyle(
            "NormalText",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#334155"),
        )
        alert_style = ParagraphStyle(
            "AlertText",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#dc2626"),
            leading=10,
        )

        elements = []

        # 1. Header Banner
        elements.append(Paragraph("TradePilot AI — Autonomous Forex Analytics", title_style))
        elements.append(Paragraph(
            f"Official Performance & Risk Audit Report | Period: {report.period_type.upper()} | "
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Mode: DEMO ONLY",
            subtitle_style
        ))
        elements.append(Spacer(1, 10))

        # 2. Executive Metrics Summary Table
        m = report.metrics
        pnl_color = "#16a34a" if m.net_pnl >= 0 else "#dc2626"
        pnl_prefix = "+" if m.net_pnl >= 0 else ""

        summary_data = [
            ["Metric", "Value", "Metric", "Value"],
            ["Net Profit/Loss", f"{pnl_prefix}${m.net_pnl:,.2f}", "Total Trades", str(m.total_trades)],
            ["Win Rate", f"{m.win_rate}%", "Profit Factor", str(m.profit_factor)],
            ["Winning Trades", str(m.winning_trades), "Losing Trades", str(m.losing_trades)],
            ["Average Win", f"${m.average_win:,.2f}", "Average Loss", f"${m.average_loss:,.2f}"],
            ["Trade Expectancy", f"${m.trade_expectancy:,.2f}", "Max Drawdown", f"{m.max_drawdown_pct}%"],
            ["Total Commission", f"${m.total_commission:,.2f}", "Total Swap", f"${m.total_swap:,.2f}"],
            ["Starting Balance", f"${report.starting_balance:,.2f}", "Ending Balance", f"${report.ending_balance:,.2f}"],
        ]

        summary_table = Table(summary_data, colWidths=[130, 140, 130, 140])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("TEXTCOLOR", (1, 1), (1, 1), colors.HexColor(pnl_color)),
            ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold"),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 15))

        # 3. Strategy Performance Breakdown
        if m.performance_by_strategy:
            elements.append(Paragraph("Performance by Adaptive Strategy", section_style))
            strat_rows = [["Strategy Name", "Total Trades", "Wins", "Win Rate", "Net P&L"]]
            for sname, sdata in m.performance_by_strategy.items():
                w_rate = round((sdata["wins"] / sdata["trades"] * 100.0), 1) if sdata["trades"] > 0 else 0.0
                strat_rows.append([
                    sname,
                    str(sdata["trades"]),
                    str(sdata["wins"]),
                    f"{w_rate}%",
                    f"${sdata['net_pnl']:,.2f}"
                ])
            strat_table = Table(strat_rows, colWidths=[160, 90, 90, 90, 110])
            strat_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f1f5f9")),
            ]))
            elements.append(strat_table)
            elements.append(Spacer(1, 15))

        # 4. Closed Trades List (Max 25 most recent in PDF printout)
        elements.append(Paragraph("Trade Execution Audit Log", section_style))
        if report.trades:
            trade_rows = [["Ticket", "Type", "Vol", "Open Price", "Close Price", "Net P&L", "Exit Reason", "Strategy"]]
            for t in report.trades[-25:]:
                t_pnl = t.get("net_pnl", 0.0)
                pnl_str = f"+${t_pnl:.2f}" if t_pnl >= 0 else f"-${abs(t_pnl):.2f}"
                trade_rows.append([
                    str(t.get("ticket", "")),
                    t.get("type", ""),
                    f"{t.get('volume', 0.0):.2f}",
                    f"{t.get('open_price', 0.0):.5f}",
                    f"{t.get('close_price', 0.0):.5f}",
                    pnl_str,
                    t.get("exit_reason", ""),
                    t.get("strategy", ""),
                ])
            trades_table = Table(trade_rows, colWidths=[55, 45, 40, 75, 75, 70, 90, 90])
            trades_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#475569")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("FONTSIZE", (0, 1), (-1, -1), 7.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]))
            elements.append(trades_table)
        else:
            elements.append(Paragraph("<i>No closed trades recorded in this period.</i>", normal_style))

        elements.append(Spacer(1, 20))

        # 5. Regulatory & Safety Disclaimer
        disclaimer_text = (
            "<b>IMPORTANT REGULATORY & DEMO-ONLY SAFETY NOTICE:</b><br/>"
            "This document is an automated report generated by TradePilot AI operating in strict DEMO-ONLY mode. "
            "All transactions reflect simulated or verified MetaTrader 5 demo accounts. "
            "Live order submission is technically blocked. Stop-loss orders do not guarantee execution without slippage. "
            "Past trading outcomes are strictly historical and do not represent a guarantee of future financial performance."
        )
        elements.append(KeepTogether([
            Paragraph(disclaimer_text, alert_style)
        ]))

        doc.build(elements)
        return output_path
