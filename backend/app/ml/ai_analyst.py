"""
AI Market Analyst Adapter
Provides structured, schema-validated reasoning summaries,
regime classifications, and candidate strategy evaluations.
Supports deterministic local fallback and external LLM endpoints.
"""
import json
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from backend.app.config import settings
from backend.app.schemas.ai import AiDecisionOutput
from backend.app.strategies.base import SignalResult, SignalType
from backend.app.ml.classifier import ml_calibrator
from backend.app.core.events import logger


class AIAnalystAdapter:
    """
    Independent AI Analyst service producing schema-validated market reports.
    """

    def __init__(self):
        self.provider = settings.AI_PROVIDER
        self.model_name = settings.AI_MODEL_NAME

    def analyze_market_state(
        self,
        symbol: str,
        regime: str,
        regime_details: Dict[str, Any],
        signal: SignalResult,
        df_candles: Any
    ) -> AiDecisionOutput:
        """
        Generate structured analysis report.
        Uses external AI provider if configured, or deterministic fallback engine.
        """
        # Try external AI provider if configured and not local_fallback
        if self.provider in {"openai", "gemini", "claude", "ollama"} and settings.AI_API_KEY:
            try:
                external_result = self._call_external_provider(
                    symbol, regime, regime_details, signal
                )
                if external_result:
                    return external_result
            except Exception as e:
                logger.warning(f"External AI provider {self.provider} failed: {e}. Falling back to deterministic analyst.")

        # Deterministic Fallback Analyst
        return self._evaluate_deterministic_analyst(
            symbol, regime, regime_details, signal, df_candles
        )

    def _evaluate_deterministic_analyst(
        self,
        symbol: str,
        regime: str,
        regime_details: Dict[str, Any],
        signal: SignalResult,
        df_candles: Any
    ) -> AiDecisionOutput:
        """
        Safe, deterministic quantitative analyst.
        Extracts calibrated probabilities from local ML model and provides
        transparent, verifiable reasoning without hallucination.
        """
        # Calibrated ML confidence
        ml_conf, ml_expectancy = ml_calibrator.predict_confidence(df_candles)

        decision_str = signal.signal_type.value  # BUY, SELL, or WAIT

        # If regime is uncertain or volatile, enforce WAIT
        if regime in {"uncertain", "high_volatility"}:
            decision_str = "WAIT"

        # Build evidence lists
        supporting = list(signal.supporting_evidence)
        contradicting = list(signal.contradicting_evidence)
        invalidations = list(signal.invalidation_conditions)

        # Append regime notes
        if regime == "trending":
            supporting.append(f"Market regime classified as TRENDING (ATR: {regime_details.get('atr', 0.001)})")
        elif regime == "ranging":
            supporting.append(f"Market regime classified as RANGING with oscillating bands")
        elif regime == "high_volatility":
            contradicting.append("High volatility expansion detected: risk of unpredictable slippage")
        else:
            contradicting.append("Regime uncertain: insufficient trend conviction")

        if ml_conf is not None:
            if decision_str == "BUY" and ml_conf > 0.55:
                supporting.append(f"ML Direction Calibrator confirms bullish tilt (score: {ml_conf})")
            elif decision_str == "SELL" and ml_conf < 0.45:
                supporting.append(f"ML Direction Calibrator confirms bearish tilt (score: {round(1.0 - ml_conf, 2)})")
            elif (decision_str == "BUY" and ml_conf < 0.45) or (decision_str == "SELL" and ml_conf > 0.55):
                contradicting.append(f"ML Calibrator conflicts with rule trigger (score: {ml_conf})")
                # When rule and ML conflict, prudently switch to WAIT
                decision_str = "WAIT"

        # Construct concise reasoning summary
        if decision_str in {"BUY", "SELL"}:
            reasoning = (
                f"Quantitative consensus for {decision_str} on {symbol}. "
                f"Strategy: {signal.strategy_name} in {regime} regime. "
                f"Entry at {signal.entry_price}, Stop Loss: {signal.stop_loss}, "
                f"Take Profit: {signal.take_profit} ({signal.risk_reward_ratio} R:R)."
            )
        else:
            reasoning = (
                f"WAIT recommended on {symbol}. {signal.reasoning_summary} "
                f"Conditions do not meet all safety and structural entry criteria."
            )

        now_iso = datetime.now(timezone.utc).isoformat()

        return AiDecisionOutput(
            symbol=symbol,
            decision=decision_str,
            market_regime=regime,
            strategy=signal.strategy_name if decision_str != "WAIT" else None,
            confidence=ml_conf,
            trade_expectancy=ml_expectancy,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            invalidation_conditions=invalidations,
            reasoning_summary=reasoning,
            feature_timestamp=now_iso,
            model_version=f"{self.model_name}+{ml_calibrator.MODEL_VERSION}"
        )

    def _call_external_provider(
        self,
        symbol: str,
        regime: str,
        regime_details: Dict[str, Any],
        signal: SignalResult
    ) -> Optional[AiDecisionOutput]:
        """
        Call OpenAI / Gemini / Ollama compatible HTTP endpoint with JSON schema prompt.
        """
        prompt_payload = {
            "symbol": symbol,
            "regime": regime,
            "regime_details": regime_details,
            "strategy_candidate": signal.strategy_name,
            "strategy_signal": signal.signal_type.value,
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
        }

        # Example Ollama / OpenAI API call template
        url = settings.AI_API_BASE or "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {settings.AI_API_KEY}", "Content-Type": "application/json"}
        body = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an AI quantitative forex risk analyst. You must evaluate the provided market state "
                        "and output strictly valid JSON matching this schema: "
                        "{symbol, decision (BUY/SELL/WAIT), market_regime, strategy, confidence (0.0-1.0), "
                        "supporting_evidence, contradicting_evidence, invalidation_conditions, reasoning_summary}."
                    )
                },
                {"role": "user", "content": json.dumps(prompt_payload)}
            ],
            "temperature": 0.1
        }

        with httpx.Client(timeout=settings.AI_TIMEOUT_SECONDS) as client:
            resp = client.post(url, headers=headers, json=body)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                parsed["feature_timestamp"] = datetime.now(timezone.utc).isoformat()
                parsed["model_version"] = f"external-{self.model_name}"
                return AiDecisionOutput.model_validate(parsed)

        return None


# Global singleton instance of AIAnalystAdapter
ai_analyst = AIAnalystAdapter()
