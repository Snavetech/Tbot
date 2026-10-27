"""
Unit tests for Reporting Engine and PDF/CSV Exporters
"""
import pytest
import os
from datetime import datetime, timezone
from backend.app.reports.generator import ReportGenerator
from backend.app.reports.pdf_export import PDFReportExporter
from backend.app.reports.csv_export import CSVReportExporter
from backend.app.models.models import TradeRecord


def test_report_generator_empty_period(test_db):
    """Report on empty period must show 0 trades and never fabricate data"""
    summary = ReportGenerator.generate_report_summary(
        db=test_db,
        period_type="all_time",
        current_equity=10000.0,
        current_balance=10000.0
    )

    assert summary.metrics.total_trades == 0
    assert summary.metrics.net_pnl == 0.0
    assert summary.metrics.win_rate == 0.0
    assert len(summary.trades) == 0
    assert "No closed trades recorded in this reporting period." in summary.data_limitations


def test_report_generator_with_trades(test_db):
    """Verify exact profit factor, win rate, and expectancy from recorded trades"""
    now = datetime.now(timezone.utc)

    # 1 Win ($100), 1 Loss ($50)
    t1 = TradeRecord(
        ticket=101, symbol="EURUSD", trade_type="BUY", volume=0.10,
        open_price=1.08500, close_price=1.08600, sl=1.08200, tp=1.08800,
        open_time=now, close_time=now, gross_pnl=100.0, net_pnl=95.0,
        commission=-5.0, exit_reason="TP", strategy_used="trend_following"
    )
    t2 = TradeRecord(
        ticket=102, symbol="EURUSD", trade_type="SELL", volume=0.10,
        open_price=1.08500, close_price=1.08550, sl=1.08600, tp=1.08300,
        open_time=now, close_time=now, gross_pnl=-50.0, net_pnl=-55.0,
        commission=-5.0, exit_reason="SL", strategy_used="trend_following"
    )
    test_db.add_all([t1, t2])
    test_db.commit()

    summary = ReportGenerator.generate_report_summary(
        db=test_db,
        period_type="all_time",
        current_equity=10040.0,
        current_balance=10040.0
    )

    m = summary.metrics
    assert m.total_trades == 2
    assert m.winning_trades == 1
    assert m.losing_trades == 1
    assert m.win_rate == 50.0
    assert m.net_pnl == 40.0  # 95 - 55 = 40
    assert m.profit_factor == round(95.0 / 55.0, 2)


def test_pdf_report_exporter(test_db, tmp_path):
    """Test PDF exporter creates valid readable PDF file"""
    summary = ReportGenerator.generate_report_summary(test_db, "daily")
    pdf_path = str(tmp_path / "test_report.pdf")

    out_file = PDFReportExporter.generate_pdf(summary, pdf_path)
    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 1000  # Non-trivial PDF size


def test_csv_report_exporter(test_db, tmp_path):
    """Test CSV exporter produces valid CSV file"""
    summary = ReportGenerator.generate_report_summary(test_db, "daily")
    csv_path = str(tmp_path / "test_trades.csv")

    out_file = CSVReportExporter.export_trades_csv(summary.trades, csv_path)
    assert os.path.exists(out_file)
