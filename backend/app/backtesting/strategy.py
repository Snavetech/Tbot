"""
Baseline EMA Trend-Following Strategy with RSI Confirmation & ATR Exits
Evaluates market signals strictly after candle close without look-ahead bias.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class SignalDecision(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"


@dataclass
class StrategyConfig:
    """
    Configurable parameters for the baseline quantitative research strategy.
    Note: These are baseline research defaults and are NOT claimed to be optimal.
    """
    fast_ema_period: int = 50
    slow_ema_period: int = 200
    rsi_period: int = 14
    rsi_long_min: float = 52.0
    rsi_long_max: float = 68.0
    rsi_short_min: float = 32.0
    rsi_short_max: float = 48.0
    atr_period: int = 14
    atr_stop_multiplier: float = 1.5
    risk_reward_ratio: float = 2.0
    min_atr_pips: float = 4.0      # Min volatility required to trade
    max_spread_pips: float = 2.5   # Spread ceiling
    cooldown_bars: int = 2         # Minimum bars between trade exit and next entry
    require_h1_alignment: bool = False
    max_open_positions: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fast_ema_period": self.fast_ema_period,
            "slow_ema_period": self.slow_ema_period,
            "rsi_period": self.rsi_period,
            "rsi_long_min": self.rsi_long_min,
            "rsi_long_max": self.rsi_long_max,
            "rsi_short_min": self.rsi_short_min,
            "rsi_short_max": self.rsi_short_max,
            "atr_period": self.atr_period,
            "atr_stop_multiplier": self.atr_stop_multiplier,
            "risk_reward_ratio": self.risk_reward_ratio,
            "min_atr_pips": self.min_atr_pips,
            "max_spread_pips": self.max_spread_pips,
            "cooldown_bars": self.cooldown_bars,
            "require_h1_alignment": self.require_h1_alignment,
            "max_open_positions": self.max_open_positions,
        }


@dataclass
class StrategySignal:
    decision: SignalDecision
    stop_distance_pips: float
    target_distance_pips: float
    reason: str
    evaluated_at_bar: int
    evaluated_at_time: int
    ema_50: float
    ema_200: float
    rsi: float
    atr: float


class BaselineTrendStrategy:
    """
    Quantitative Trend-Following Strategy:
    - Long condition:
        1. Fast EMA (50) > Slow EMA (200) (Bullish Trend)
        2. Close > Fast EMA (50) (Price trading above mean)
        3. RSI between rsi_long_min and rsi_long_max (Positive momentum without overbought extreme)
        4. Spread <= max_spread_pips
        5. (Optional) H1 trend is also UP
    - Short condition:
        1. Fast EMA (50) < Slow EMA (200) (Bearish Trend)
        2. Close < Fast EMA (50) (Price trading below mean)
        3. RSI between rsi_short_min and rsi_short_max (Negative momentum without oversold extreme)
        4. Spread <= max_spread_pips
        5. (Optional) H1 trend is also DOWN
    """

    def __init__(self, config: Optional[StrategyConfig] = None):
        self.config = config or StrategyConfig()

    def evaluate_bar(
        self,
        bar_idx: int,
        bar_data: Dict[str, Any],
        current_spread_pips: float = 1.2
    ) -> StrategySignal:
        """
        Evaluates a closed candle for entry signals.
        bar_data must contain precomputed indicators: ema_50, ema_200, rsi_14, atr_14, is_warmup.
        """
        bar_time = int(bar_data.get("time", 0))

        # Check warm-up period
        if bar_data.get("is_warmup", False):
            return StrategySignal(
                decision=SignalDecision.WAIT,
                stop_distance_pips=0.0,
                target_distance_pips=0.0,
                reason="Warm-up period active (indicator values not yet statistically mature)",
                evaluated_at_bar=bar_idx,
                evaluated_at_time=bar_time,
                ema_50=0.0, ema_200=0.0, rsi=50.0, atr=0.0
            )

        ema_50 = float(bar_data.get("ema_50", 0.0))
        ema_200 = float(bar_data.get("ema_200", 0.0))
        rsi = float(bar_data.get("rsi_14", 50.0))
        atr = float(bar_data.get("atr_14", 0.0))
        close = float(bar_data.get("close", 0.0))

        atr_pips = atr / 0.0001
        cfg = self.config

        # Volatility & Spread gates
        if atr_pips < cfg.min_atr_pips:
            return StrategySignal(
                decision=SignalDecision.WAIT,
                stop_distance_pips=0.0,
                target_distance_pips=0.0,
                reason=f"Volatility too low: ATR ({atr_pips:.1f} pips) < min ({cfg.min_atr_pips:.1f} pips)",
                evaluated_at_bar=bar_idx,
                evaluated_at_time=bar_time,
                ema_50=ema_50, ema_200=ema_200, rsi=rsi, atr=atr
            )

        if current_spread_pips > cfg.max_spread_pips:
            return StrategySignal(
                decision=SignalDecision.WAIT,
                stop_distance_pips=0.0,
                target_distance_pips=0.0,
                reason=f"Spread too wide: {current_spread_pips:.1f} pips > max {cfg.max_spread_pips:.1f} pips",
                evaluated_at_bar=bar_idx,
                evaluated_at_time=bar_time,
                ema_50=ema_50, ema_200=ema_200, rsi=rsi, atr=atr
            )

        # Higher timeframe filter
        h1_trend = bar_data.get("h1_trend_direction", "UNKNOWN")
        if cfg.require_h1_alignment:
            if h1_trend == "UNKNOWN":
                return StrategySignal(
                    decision=SignalDecision.WAIT,
                    stop_distance_pips=0.0, target_distance_pips=0.0,
                    reason="H1 trend alignment required but H1 data is unavailable",
                    evaluated_at_bar=bar_idx, evaluated_at_time=bar_time,
                    ema_50=ema_50, ema_200=ema_200, rsi=rsi, atr=atr
                )

        # Dynamic Stop & Target Distances
        stop_dist_pips = round(atr_pips * cfg.atr_stop_multiplier, 1)
        target_dist_pips = round(stop_dist_pips * cfg.risk_reward_ratio, 1)

        # 1. Bullish Evaluation
        if ema_50 > ema_200 and close > ema_50:
            if cfg.rsi_long_min <= rsi <= cfg.rsi_long_max:
                if not cfg.require_h1_alignment or h1_trend == "UP":
                    return StrategySignal(
                        decision=SignalDecision.BUY,
                        stop_distance_pips=stop_dist_pips,
                        target_distance_pips=target_dist_pips,
                        reason=f"Bullish trend (EMA50 > EMA200) + RSI momentum confirmation ({rsi:.1f})",
                        evaluated_at_bar=bar_idx,
                        evaluated_at_time=bar_time,
                        ema_50=ema_50, ema_200=ema_200, rsi=rsi, atr=atr
                    )

        # 2. Bearish Evaluation
        if ema_50 < ema_200 and close < ema_50:
            if cfg.rsi_short_min <= rsi <= cfg.rsi_short_max:
                if not cfg.require_h1_alignment or h1_trend == "DOWN":
                    return StrategySignal(
                        decision=SignalDecision.SELL,
                        stop_distance_pips=stop_dist_pips,
                        target_distance_pips=target_dist_pips,
                        reason=f"Bearish trend (EMA50 < EMA200) + RSI momentum confirmation ({rsi:.1f})",
                        evaluated_at_bar=bar_idx,
                        evaluated_at_time=bar_time,
                        ema_50=ema_50, ema_200=ema_200, rsi=rsi, atr=atr
                    )

        # Default Neutral Decision
        return StrategySignal(
            decision=SignalDecision.WAIT,
            stop_distance_pips=0.0,
            target_distance_pips=0.0,
            reason="Market conditions neutral; baseline criteria not triggered",
            evaluated_at_bar=bar_idx,
            evaluated_at_time=bar_time,
            ema_50=ema_50, ema_200=ema_200, rsi=rsi, atr=atr
        )
