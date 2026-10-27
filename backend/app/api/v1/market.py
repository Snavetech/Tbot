"""
Market Data & Price Feed endpoints
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from backend.app.config import settings
from backend.app.services.mt5_adapter import mt5_adapter
from backend.app.services.market_data import MarketDataService
from backend.app.schemas.market import (
    CandleSchema, TickerSchema, IndicatorValues, MarketOverviewResponse
)

router = APIRouter(prefix="/market", tags=["Market Data"])


@router.get("/ticker", response_model=TickerSchema)
def get_ticker(symbol: str = Query(default="EURUSD")):
    """Get current Bid, Ask, Spread and freshness status"""
    try:
        data = mt5_adapter.get_ticker(symbol)
        return TickerSchema(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/candles", response_model=List[CandleSchema])
def get_candles(
    symbol: str = Query(default="EURUSD"),
    timeframe: str = Query(default="M15"),
    count: int = Query(default=200, ge=10, le=1000)
):
    """Retrieve historical closed candles"""
    try:
        df = mt5_adapter.get_candles(symbol, timeframe=timeframe, count=count)
        records = df.to_dict(orient="records")
        return [CandleSchema(**r) for r in records]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators", response_model=IndicatorValues)
def get_indicators(
    symbol: str = Query(default="EURUSD"),
    timeframe: str = Query(default="M15")
):
    """Get latest technical indicators and regime for symbol"""
    try:
        df = mt5_adapter.get_candles(symbol, timeframe=timeframe, count=100)
        df_ind = MarketDataService.calculate_indicators(df)
        regime, _ = MarketDataService.classify_regime(df_ind)

        latest = df_ind.iloc[-1]
        return IndicatorValues(
            time=int(latest["time"]),
            ema_fast=round(float(latest.get("ema_fast", 0.0)), 5) if pd_not_na(latest.get("ema_fast")) else None,
            ema_slow=round(float(latest.get("ema_slow", 0.0)), 5) if pd_not_na(latest.get("ema_slow")) else None,
            rsi=round(float(latest.get("rsi", 0.0)), 1) if pd_not_na(latest.get("rsi")) else None,
            atr=round(float(latest.get("atr", 0.0)), 5) if pd_not_na(latest.get("atr")) else None,
            bb_upper=round(float(latest.get("bb_upper", 0.0)), 5) if pd_not_na(latest.get("bb_upper")) else None,
            bb_middle=round(float(latest.get("bb_middle", 0.0)), 5) if pd_not_na(latest.get("bb_middle")) else None,
            bb_lower=round(float(latest.get("bb_lower", 0.0)), 5) if pd_not_na(latest.get("bb_lower")) else None,
            support_level=round(float(latest.get("support", 0.0)), 5) if pd_not_na(latest.get("support")) else None,
            resistance_level=round(float(latest.get("resistance", 0.0)), 5) if pd_not_na(latest.get("resistance")) else None,
            regime=regime
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview", response_model=MarketOverviewResponse)
def get_market_overview(
    symbol: str = Query(default="EURUSD"),
    timeframe: str = Query(default="M15")
):
    """Combined market overview: ticker, indicators and recent candles"""
    ticker = get_ticker(symbol)
    candles = get_candles(symbol, timeframe, count=120)
    indicators = get_indicators(symbol, timeframe)

    return MarketOverviewResponse(
        symbol=symbol,
        ticker=ticker,
        indicators=indicators,
        candles=candles
    )


def pd_not_na(val) -> bool:
    import pandas as pd
    return val is not None and not pd.isna(val)
