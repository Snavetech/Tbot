"""
System health and status endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.app.config import settings
from backend.app.core.database import get_db
from backend.app.services.mt5_adapter import mt5_adapter
from backend.app.services.scheduler import engine_scheduler
from backend.app.models.models import AuditEvent

router = APIRouter(prefix="", tags=["Health & System"])


@router.get("/health")
def health_check():
    """Basic health check probe"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "mode": settings.TRADING_MODE,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/system/status")
def system_status(db: Session = Depends(get_db)):
    """Comprehensive system health, database state, and audit logs"""
    recent_events = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(15).all()

    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "trading_mode": settings.TRADING_MODE,
        "live_trading_enabled": settings.LIVE_TRADING_ENABLED,
        "mt5_connected": mt5_adapter.is_connected,
        "mt5_is_mock": mt5_adapter.is_mock,
        "bot_state": engine_scheduler.state_machine.to_dict(),
        "database_status": "connected",
        "recent_audit_events": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type,
                "severity": e.severity,
                "message": e.message,
                "metadata": e.metadata_json,
            }
            for e in recent_events
        ]
    }
