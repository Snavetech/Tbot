"""
Reporting, Analytics, and PDF/CSV Export endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import os

from backend.app.core.database import get_db
from backend.app.services.mt5_adapter import mt5_adapter
from backend.app.reports.generator import ReportGenerator
from backend.app.reports.pdf_export import PDFReportExporter
from backend.app.reports.csv_export import CSVReportExporter
from backend.app.schemas.reports import ReportSummaryResponse

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


@router.get("/summary", response_model=ReportSummaryResponse)
def get_report_summary(
    period: str = Query(default="all_time", pattern="^(daily|weekly|monthly|all_time)$"),
    db: Session = Depends(get_db)
):
    """Generate performance summary metrics for specified period"""
    equity = 10000.0
    balance = 10000.0
    if mt5_adapter.is_connected:
        try:
            acc = mt5_adapter.get_account_info()
            equity = acc.get("equity", 10000.0)
            balance = acc.get("balance", 10000.0)
        except Exception:
            pass

    return ReportGenerator.generate_report_summary(
        db=db,
        period_type=period,
        current_equity=equity,
        current_balance=balance
    )


@router.get("/pdf")
def download_pdf_report(
    period: str = Query(default="all_time", pattern="^(daily|weekly|monthly|all_time)$"),
    db: Session = Depends(get_db)
):
    """Generate and download audit-ready PDF performance report"""
    summary = get_report_summary(period=period, db=db)
    filename = f"tradepilot_report_{period}_{int(datetime.now(timezone.utc).timestamp())}.pdf"
    file_path = os.path.abspath(f"./data/reports/{filename}")

    PDFReportExporter.generate_pdf(summary, file_path)

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename
    )


@router.get("/csv")
def download_csv_report(
    period: str = Query(default="all_time", pattern="^(daily|weekly|monthly|all_time)$"),
    db: Session = Depends(get_db)
):
    """Generate and download trades CSV export"""
    summary = get_report_summary(period=period, db=db)
    filename = f"tradepilot_trades_{period}_{int(datetime.now(timezone.utc).timestamp())}.csv"
    file_path = os.path.abspath(f"./data/reports/{filename}")

    CSVReportExporter.export_trades_csv(summary.trades, file_path)

    return FileResponse(
        path=file_path,
        media_type="text/csv",
        filename=filename
    )
