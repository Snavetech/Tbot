"""
Trading execution, order, position and signal schemas
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class SignalResponse(BaseModel):
    id: str
    timestamp: datetime
    symbol: str
    timeframe: str
    strategy_name: str
    signal_type: str  # BUY, SELL, WAIT
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    strategy_version: str
    is_executed: bool
    rejection_reason: Optional[str] = None


class OrderResponse(BaseModel):
    client_order_id: str
    broker_order_id: Optional[int]
    timestamp: datetime
    symbol: str
    order_type: str
    volume: float
    requested_price: float
    executed_price: Optional[float]
    sl: float
    tp: float
    status: str
    retcode: Optional[int]
    broker_comment: Optional[str]


class PositionResponse(BaseModel):
    ticket: int
    symbol: str
    position_type: str
    volume: float
    open_price: float
    current_price: float
    sl: float
    tp: float
    swap: float
    commission: float
    profit: float
    open_time: datetime
    status: str
    strategy_used: Optional[str]
    signal_id: Optional[str]


class TradeResponse(BaseModel):
    id: int
    ticket: int
    symbol: str
    trade_type: str
    volume: float
    open_price: float
    close_price: float
    sl: float
    tp: float
    open_time: datetime
    close_time: datetime
    gross_pnl: float
    net_pnl: float
    commission: float
    swap: float
    slippage: float
    exit_reason: str
    strategy_used: str
    model_version: str
    market_regime: str


class EmergencyFlattenRequest(BaseModel):
    confirmation: str = Field(..., description="Must explicitly be 'FLATTEN_ALL_DEMO_POSITIONS'")
    reason: str = Field(..., min_length=5, description="Audited reason for emergency closure")
