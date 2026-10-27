"""
Bot state and control schemas
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class BotStateResponse(BaseModel):
    current_state: str
    previous_state: Optional[str]
    last_transition_time: str
    transition_reason: str
    error_message: Optional[str]
    can_enter_trades: bool
    can_monitor_positions: bool
    is_evaluating: bool
    mt5_connected: bool
    is_demo_account: bool


class StateTransitionRequest(BaseModel):
    action: str = Field(..., description="Action: start, pause, stop, unlock_risk")
    reason: str = Field(default="User command via dashboard", min_length=3)
