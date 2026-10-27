"""
Event dispatcher and persistent audit logging service
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

# Configure root logger for backend
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("tradepilot")


class AuditService:
    """Manages audit logging and persistent event recording"""

    @staticmethod
    def log_event(
        db: Optional[Session],
        event_type: str,
        message: str,
        severity: str = "INFO",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log event to logger and optionally persist to AuditEvent table"""
        # Ensure secrets are sanitized
        sanitized_meta = AuditService.sanitize_metadata(metadata or {})
        log_msg = f"[{event_type}] {message} | Details: {sanitized_meta}"

        if severity == "ERROR":
            logger.error(log_msg)
        elif severity == "WARNING":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        if db:
            try:
                from backend.app.models.models import AuditEvent
                audit_record = AuditEvent(
                    timestamp=datetime.now(timezone.utc),
                    event_type=event_type,
                    severity=severity,
                    message=message,
                    metadata_json=sanitized_meta
                )
                db.add(audit_record)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to persist audit event to database: {e}")

    @staticmethod
    def sanitize_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
        """Strip any password, token, or secret from audit metadata"""
        sensitive_keys = {"password", "secret", "token", "key", "api_key", "credentials"}
        sanitized = {}
        for k, v in meta.items():
            if any(s in k.lower() for s in sensitive_keys):
                sanitized[k] = "***REDACTED***"
            elif isinstance(v, dict):
                sanitized[k] = AuditService.sanitize_metadata(v)
            else:
                sanitized[k] = v
        return sanitized
