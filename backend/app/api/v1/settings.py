"""
Settings & configuration endpoints
"""
from fastapi import APIRouter, Depends, Body
from typing import Dict, Any

from backend.app.config import settings
from backend.app.core.security import verify_control_access

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("")
def get_settings():
    """Retrieve non-sensitive platform settings and symbol mapping"""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "trading_mode": settings.TRADING_MODE,
        "live_trading_enabled": settings.LIVE_TRADING_ENABLED,
        "allowed_symbols": settings.ALLOWED_SYMBOLS,
        "default_symbol": settings.DEFAULT_SYMBOL,
        "default_timeframe": settings.DEFAULT_TIMEFRAME,
        "htf_timeframe": settings.HTF_TIMEFRAME,
        "symbol_map": settings.MT5_SYMBOL_MAP,
        "ai_provider": settings.AI_PROVIDER,
        "ai_model_name": settings.AI_MODEL_NAME,
        "max_risk_per_trade_pct": settings.MAX_RISK_PER_TRADE_PCT,
        "max_total_open_risk_pct": settings.MAX_TOTAL_OPEN_RISK_PCT,
        "max_daily_loss_pct": settings.MAX_DAILY_LOSS_PCT,
        "max_weekly_loss_pct": settings.MAX_WEEKLY_LOSS_PCT,
        "max_consecutive_losses": settings.MAX_CONSECUTIVE_LOSSES,
        "max_trades_per_day": settings.MAX_TRADES_PER_DAY,
        "max_spread_pips": settings.MAX_SPREAD_PIPS,
    }


@router.post("/symbol-map", dependencies=[Depends(verify_control_access)])
def update_symbol_map(mapping: Dict[str, str] = Body(...)):
    """Update broker-specific symbol mapping"""
    settings.MT5_SYMBOL_MAP.update(mapping)
    return {"success": True, "symbol_map": settings.MT5_SYMBOL_MAP}
