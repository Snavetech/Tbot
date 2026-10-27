"""
AI Market Analysis & Strategy Decision Endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.core.database import get_db
from backend.app.services.mt5_adapter import mt5_adapter
from backend.app.services.market_data import MarketDataService
from backend.app.strategies.engine import strategy_engine
from backend.app.ml.ai_analyst import ai_analyst
from backend.app.schemas.ai import AiDecisionOutput
from backend.app.models.models import AiAnalysisRecord, SignalRecord

router = APIRouter(prefix="/analysis", tags=["AI Market Analysis"])


@router.get("/latest", response_model=AiDecisionOutput)
def get_latest_analysis(db: Session = Depends(get_db)):
    """Fetch most recent persisted AI analysis record"""
    record = db.query(AiAnalysisRecord).order_by(AiAnalysisRecord.timestamp.desc()).first()
    if not record:
        # Generate immediate fresh analysis if no record exists
        return evaluate_analysis(symbol="EURUSD", db=db)

    return AiDecisionOutput(
        symbol=record.symbol,
        decision=record.decision,
        market_regime=record.market_regime,
        strategy=record.strategy,
        confidence=record.confidence,
        trade_expectancy=record.trade_expectancy,
        supporting_evidence=record.supporting_evidence or [],
        contradicting_evidence=record.contradicting_evidence or [],
        invalidation_conditions=record.invalidation_conditions or [],
        reasoning_summary=record.reasoning_summary,
        feature_timestamp=record.feature_timestamp.isoformat() if record.feature_timestamp else None,
        model_version=record.model_version
    )


@router.post("/evaluate", response_model=AiDecisionOutput)
def evaluate_analysis(
    symbol: str = Query(default="EURUSD"),
    db: Session = Depends(get_db)
):
    """Run on-demand AI analysis on current market state"""
    try:
        df_m15 = mt5_adapter.get_candles(symbol, timeframe="M15", count=120)
        df_h1 = mt5_adapter.get_candles(symbol, timeframe="H1", count=60)
        ticker = mt5_adapter.get_ticker(symbol)

        df_m15_ind = MarketDataService.calculate_indicators(df_m15)
        regime, regime_details = MarketDataService.classify_regime(df_m15_ind)

        signal = strategy_engine.evaluate_market(
            symbol=symbol,
            df_m15=df_m15,
            df_h1=df_h1,
            current_spread_pips=ticker["spread_pips"]
        )

        analysis = ai_analyst.analyze_market_state(
            symbol=symbol,
            regime=regime,
            regime_details=regime_details,
            signal=signal,
            df_candles=df_m15_ind
        )

        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis evaluation failed: {e}")


@router.get("/strategies")
def list_strategies():
    """List registered strategies and current status"""
    return {
        "strategies": [
            {
                "name": "trend_following",
                "version": strategy_engine.trend_strategy.version,
                "description": "M15 EMA pullback with H1 trend alignment, RSI momentum confirmation and ATR stops",
                "active_regime": "trending",
                "is_active": True
            },
            {
                "name": "range_bound",
                "version": strategy_engine.range_strategy.version,
                "description": "Bollinger Bands and Support/Resistance boundary rejection with mean reversion",
                "active_regime": "ranging",
                "is_active": True
            }
        ],
        "default_symbol": settings.DEFAULT_SYMBOL,
        "entry_timeframe": settings.DEFAULT_TIMEFRAME,
        "htf_timeframe": settings.HTF_TIMEFRAME,
    }
