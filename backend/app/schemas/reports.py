"""
Reports and performance analytics schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class PerformanceMetrics(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    gross_profit: float
    gross_loss: float
    net_pnl: float
    total_commission: float
    total_swap: float
    average_win: float
    average_loss: float
    trade_expectancy: float
    max_drawdown_amount: float
    max_drawdown_pct: float
    performance_by_strategy: Dict[str, Any] = Field(default_factory=dict)
    performance_by_regime: Dict[str, Any] = Field(default_factory=dict)


class EquityPoint(BaseModel):
    timestamp: str
    equity: float
    balance: float
    drawdown_pct: float


class ReportSummaryResponse(BaseModel):
    period_type: str  # daily, weekly, monthly, all_time
    period_start: str
    period_end: str
    timezone: str = "UTC"
    starting_balance: float
    ending_balance: float
    starting_equity: float
    ending_equity: float
    metrics: PerformanceMetrics
    equity_curve: List[EquityPoint]
    trades: List[dict]
    data_limitations: List[str] = Field(default_factory=list)


class BacktestRequest(BaseModel):
    symbol: str = "EURUSD"
    timeframe: str = "M15"
    strategy_name: str = "all"  # trend_following, range_bound, all
    start_bars: int = Field(default=1000, ge=100, le=10000)
    initial_balance: float = Field(default=10000.0, ge=1000.0)
    spread_pips: float = Field(default=1.2, ge=0.1, le=10.0)
    slippage_points: int = Field(default=5, ge=0, le=50)
    commission_per_lot: float = Field(default=7.0, ge=0.0)
