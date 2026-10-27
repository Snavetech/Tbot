"""
Market data schemas
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class CandleSchema(BaseModel):
    time: int = Field(..., description="UNIX timestamp in seconds")
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class TickerSchema(BaseModel):
    symbol: str
    bid: float
    ask: float
    spread: float
    spread_pips: float
    time: int
    is_stale: bool = False


class IndicatorValues(BaseModel):
    time: int
    ema_fast: Optional[float] = None
    ema_slow: Optional[float] = None
    rsi: Optional[float] = None
    atr: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    regime: str = "uncertain"


class MarketOverviewResponse(BaseModel):
    symbol: str
    ticker: TickerSchema
    indicators: IndicatorValues
    candles: List[CandleSchema]
