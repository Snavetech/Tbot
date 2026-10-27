"""
Risk engine schemas and validation models
"""
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class RiskStatusResponse(BaseModel):
    max_risk_per_trade_pct: float
    max_total_open_risk_pct: float
    current_open_risk_pct: float
    daily_loss_pct: float
    max_daily_loss_pct: float
    weekly_loss_pct: float
    max_weekly_loss_pct: float
    consecutive_losses: int
    max_consecutive_losses: int
    trades_today: int
    max_trades_per_day: int
    is_locked: bool
    lock_reason: Optional[str] = None
    account_equity: float
    account_balance: float
    free_margin: float
    spread_pips: float
    max_spread_pips: float
    can_trade: bool
    rejection_reasons: List[str] = Field(default_factory=list)


class RiskSettingsUpdate(BaseModel):
    max_risk_per_trade_pct: Optional[float] = Field(default=None, ge=0.05, le=1.0)
    max_total_open_risk_pct: Optional[float] = Field(default=None, ge=0.10, le=2.0)
    max_daily_loss_pct: Optional[float] = Field(default=None, ge=0.20, le=5.0)
    max_weekly_loss_pct: Optional[float] = Field(default=None, ge=0.50, le=10.0)
    max_consecutive_losses: Optional[int] = Field(default=None, ge=1, le=10)
    max_trades_per_day: Optional[int] = Field(default=None, ge=1, le=50)
    max_spread_pips: Optional[float] = Field(default=None, ge=0.5, le=10.0)

    @field_validator("max_risk_per_trade_pct")
    @classmethod
    def validate_risk_trade(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v > 1.0:
            raise ValueError("Risk per trade cannot exceed 1.0% in demo safety policy.")
        return v


class RiskCheckResult(BaseModel):
    is_approved: bool
    approved_volume: float
    requested_volume: float
    risk_amount: float
    risk_pct: float
    stop_loss_distance_pips: float
    rejection_reason: Optional[str] = None
    details: dict = Field(default_factory=dict)
