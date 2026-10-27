"""
Risk Management Engine endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import verify_control_access
from backend.app.core.events import AuditService
from backend.app.config import settings
from backend.app.services.risk_engine import risk_engine
from backend.app.services.mt5_adapter import mt5_adapter
from backend.app.schemas.risk import RiskStatusResponse, RiskSettingsUpdate

router = APIRouter(prefix="/risk", tags=["Risk Management"])


@router.get("/status", response_model=RiskStatusResponse)
def get_risk_status():
    """Retrieve live risk parameters, limits, and safety locks"""
    account_info = mt5_adapter.get_account_info() if mt5_adapter.is_connected else {
        "equity": 10000.0,
        "balance": 10000.0,
        "free_margin": 10000.0,
    }
    ticker = mt5_adapter.get_ticker("EURUSD") if mt5_adapter.is_connected else {"spread_pips": 1.2}
    open_positions = mt5_adapter.get_open_positions() if mt5_adapter.is_connected else []

    return risk_engine.get_status(
        account_info=account_info,
        current_spread_pips=ticker.get("spread_pips", 1.2),
        open_positions=open_positions
    )


@router.post("/settings", dependencies=[Depends(verify_control_access)])
def update_risk_settings(update: RiskSettingsUpdate, db: Session = Depends(get_db)):
    """Validated update of risk parameters (enforces safe boundaries)"""
    updated_fields = {}

    if update.max_risk_per_trade_pct is not None:
        settings.MAX_RISK_PER_TRADE_PCT = update.max_risk_per_trade_pct
        updated_fields["MAX_RISK_PER_TRADE_PCT"] = update.max_risk_per_trade_pct

    if update.max_total_open_risk_pct is not None:
        settings.MAX_TOTAL_OPEN_RISK_PCT = update.max_total_open_risk_pct
        updated_fields["MAX_TOTAL_OPEN_RISK_PCT"] = update.max_total_open_risk_pct

    if update.max_daily_loss_pct is not None:
        settings.MAX_DAILY_LOSS_PCT = update.max_daily_loss_pct
        updated_fields["MAX_DAILY_LOSS_PCT"] = update.max_daily_loss_pct

    if update.max_weekly_loss_pct is not None:
        settings.MAX_WEEKLY_LOSS_PCT = update.max_weekly_loss_pct
        updated_fields["MAX_WEEKLY_LOSS_PCT"] = update.max_weekly_loss_pct

    if update.max_consecutive_losses is not None:
        settings.MAX_CONSECUTIVE_LOSSES = update.max_consecutive_losses
        updated_fields["MAX_CONSECUTIVE_LOSSES"] = update.max_consecutive_losses

    if update.max_trades_per_day is not None:
        settings.MAX_TRADES_PER_DAY = update.max_trades_per_day
        updated_fields["MAX_TRADES_PER_DAY"] = update.max_trades_per_day

    if update.max_spread_pips is not None:
        settings.MAX_SPREAD_PIPS = update.max_spread_pips
        updated_fields["MAX_SPREAD_PIPS"] = update.max_spread_pips

    AuditService.log_event(
        db,
        "RISK_SETTINGS_UPDATED",
        f"Risk parameters updated: {updated_fields}",
        severity="INFO"
    )

    return {
        "success": True,
        "updated": updated_fields
    }


@router.post("/unlock", dependencies=[Depends(verify_control_access)])
def unlock_risk(db: Session = Depends(get_db)):
    """Reset risk engine safety lock after authorized review"""
    success, msg = risk_engine.unlock(authorized_by="dashboard_user")
    AuditService.log_event(db, "RISK_UNLOCKED", msg, severity="WARNING")
    return {"success": success, "message": msg}
