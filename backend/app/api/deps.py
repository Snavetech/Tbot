"""
FastAPI dependencies
"""
from backend.app.core.database import get_db
from backend.app.core.security import verify_control_access
from backend.app.services.mt5_adapter import mt5_adapter
from backend.app.services.risk_engine import risk_engine
from backend.app.services.scheduler import engine_scheduler
from backend.app.services.execution_gateway import execution_gateway
