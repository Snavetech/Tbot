"""
AI and Machine Learning schemas conforming strictly to prompt specifications
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class AiDecisionOutput(BaseModel):
    """
    Schema-validated structured AI analyst output.
    Prompt Section 7 strict requirements.
    """
    symbol: str = Field(..., description="Currency symbol, e.g. EURUSD")
    decision: str = Field(..., description="BUY, SELL, or WAIT")
    market_regime: str = Field(..., description="trending, ranging, high_volatility, or uncertain")
    strategy: Optional[str] = Field(default=None, description="Active strategy name or null")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Model confidence 0.0 - 1.0")
    trade_expectancy: Optional[float] = Field(default=None, description="Estimated trade expectancy if validated")
    supporting_evidence: List[str] = Field(default_factory=list, description="Reasons supporting decision")
    contradicting_evidence: List[str] = Field(default_factory=list, description="Reasons against decision")
    invalidation_conditions: List[str] = Field(default_factory=list, description="Conditions invalidating setup")
    reasoning_summary: str = Field(..., min_length=3, description="Summary of reasoning")
    feature_timestamp: Optional[str] = Field(default=None, description="ISO timestamp of analyzed features")
    model_version: Optional[str] = Field(default="tradepilot-deterministic-v1", description="Model identifier")

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        upper = v.upper()
        if upper not in {"BUY", "SELL", "WAIT"}:
            raise ValueError(f"Invalid decision: '{v}'. Must be BUY, SELL, or WAIT.")
        return upper

    @field_validator("market_regime")
    @classmethod
    def validate_regime(cls, v: str) -> str:
        valid_regimes = {"trending", "ranging", "high_volatility", "uncertain"}
        lower = v.lower()
        if lower not in valid_regimes:
            raise ValueError(f"Invalid market regime: '{v}'. Must be one of {valid_regimes}")
        return lower
