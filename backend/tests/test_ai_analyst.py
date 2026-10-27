"""
Unit tests for AI Analyst and Machine Learning Calibrator
"""
import pytest
from backend.app.schemas.ai import AiDecisionOutput
from backend.app.ml.ai_analyst import AIAnalystAdapter
from backend.app.strategies.base import SignalResult, SignalType
from backend.app.ml.classifier import MLCalibrator


def test_ai_schema_validation_success():
    """Verify structured output strictly conforms to prompt specification"""
    valid_data = {
        "symbol": "EURUSD",
        "decision": "WAIT",
        "market_regime": "uncertain",
        "strategy": None,
        "confidence": None,
        "supporting_evidence": [],
        "contradicting_evidence": ["Conflicting momentum"],
        "invalidation_conditions": [],
        "reasoning_summary": "Insufficient validated evidence",
        "feature_timestamp": None,
        "model_version": "tradepilot-deterministic-v1"
    }
    output = AiDecisionOutput.model_validate(valid_data)
    assert output.decision == "WAIT"
    assert output.market_regime == "uncertain"


def test_ai_schema_rejects_invalid_decision():
    """Schema must reject invalid decisions (e.g. HOLD, CLOSE)"""
    invalid_data = {
        "symbol": "EURUSD",
        "decision": "HOLD",  # Invalid!
        "market_regime": "trending",
        "reasoning_summary": "Test",
    }
    with pytest.raises(ValueError):
        AiDecisionOutput.model_validate(invalid_data)


def test_ai_schema_rejects_invalid_regime():
    """Schema must reject non-whitelisted market regimes"""
    invalid_data = {
        "symbol": "EURUSD",
        "decision": "BUY",
        "market_regime": "super_bullish",  # Invalid!
        "reasoning_summary": "Test",
    }
    with pytest.raises(ValueError):
        AiDecisionOutput.model_validate(invalid_data)


def test_ai_analyst_deterministic_fallback(sample_eurusd_candles):
    """Analyst falls back gracefully to deterministic quantitative evaluation"""
    analyst = AIAnalystAdapter()
    signal = SignalResult(
        signal_type=SignalType.WAIT,
        symbol="EURUSD",
        strategy_name="trend_following",
        entry_price=1.08500,
        stop_loss=0.0,
        take_profit=0.0,
        reasoning_summary="No pullback detected"
    )

    output = analyst.analyze_market_state(
        symbol="EURUSD",
        regime="trending",
        regime_details={"atr": 0.0012},
        signal=signal,
        df_candles=sample_eurusd_candles
    )

    assert isinstance(output, AiDecisionOutput)
    assert output.decision == "WAIT"
    assert output.symbol == "EURUSD"
    assert output.model_version is not None
