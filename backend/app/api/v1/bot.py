"""
Bot lifecycle control and emergency actions
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import verify_control_access
from backend.app.core.state_machine import BotState
from backend.app.core.events import AuditService
from backend.app.services.scheduler import engine_scheduler
from backend.app.services.execution_gateway import execution_gateway
from backend.app.services.mt5_adapter import mt5_adapter
from backend.app.schemas.state import BotStateResponse, StateTransitionRequest
from backend.app.schemas.trading import EmergencyFlattenRequest

router = APIRouter(prefix="/bot", tags=["Bot Controls"])


@router.get("/state", response_model=BotStateResponse)
def get_bot_state():
    """Retrieve full bot runtime state and execution permissions"""
    state_dict = engine_scheduler.state_machine.to_dict()
    return BotStateResponse(
        current_state=state_dict["current_state"],
        previous_state=state_dict["previous_state"],
        last_transition_time=state_dict["last_transition_time"],
        transition_reason=state_dict["transition_reason"],
        error_message=state_dict["error_message"],
        can_enter_trades=state_dict["can_enter_trades"],
        can_monitor_positions=state_dict["can_monitor_positions"],
        is_evaluating=state_dict["is_evaluating"],
        mt5_connected=mt5_adapter.is_connected,
        is_demo_account=mt5_adapter.get_account_info().get("is_demo", True) if mt5_adapter.is_connected else False,
    )


@router.post("/start", dependencies=[Depends(verify_control_access)])
def start_bot(req: StateTransitionRequest, db: Session = Depends(get_db)):
    """Start autonomous demo trading execution"""
    sm = engine_scheduler.state_machine

    if not mt5_adapter.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot start bot: MetaTrader 5 terminal is disconnected."
        )

    acc = mt5_adapter.get_account_info()
    if not acc.get("is_demo", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SAFETY REFUSAL: Connected account is not a verified demo account."
        )

    # Reconcile existing positions before entering RUNNING state
    execution_gateway.reconcile_positions(db)

    try:
        sm.transition_to(BotState.RUNNING, req.reason)
        AuditService.log_event(db, "BOT_STARTED", f"Bot transitioned to RUNNING: {req.reason}", severity="INFO")
        return {"success": True, "state": sm.current_state.value, "reason": req.reason}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pause", dependencies=[Depends(verify_control_access)])
def pause_bot(req: StateTransitionRequest, db: Session = Depends(get_db)):
    """Pause autonomous trading (maintains active position monitoring)"""
    sm = engine_scheduler.state_machine
    try:
        sm.transition_to(BotState.PAUSED, req.reason)
        AuditService.log_event(db, "BOT_PAUSED", f"Bot paused: {req.reason}", severity="INFO")
        return {"success": True, "state": sm.current_state.value, "reason": req.reason}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop", dependencies=[Depends(verify_control_access)])
def stop_bot(req: StateTransitionRequest, db: Session = Depends(get_db)):
    """Stop trading engine safely without flattening positions"""
    sm = engine_scheduler.state_machine
    try:
        sm.transition_to(BotState.STOPPING, req.reason)
        sm.transition_to(BotState.READY, "Engine stopped safely by user command")
        AuditService.log_event(db, "BOT_STOPPED", f"Bot stopped: {req.reason}", severity="INFO")
        return {"success": True, "state": sm.current_state.value, "reason": req.reason}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/emergency-flatten", dependencies=[Depends(verify_control_access)])
def emergency_flatten(req: EmergencyFlattenRequest, db: Session = Depends(get_db)):
    """Emergency flatten: close all open demo positions with explicit confirmation"""
    success, msg, details = execution_gateway.emergency_flatten_all(
        confirmation=req.confirmation,
        reason=req.reason,
        db=db
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)

    return {
        "success": True,
        "message": msg,
        "closed_positions": details
    }
