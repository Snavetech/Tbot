"""
Adaptive Strategy Engine: orchestrates regime classification and adaptive strategy execution
"""
from typing import Dict, Any, Optional, List
import pandas as pd

from backend.app.services.market_data import MarketDataService
from backend.app.strategies.base import BaseStrategy, SignalResult, SignalType
from backend.app.strategies.trend_following import TrendFollowingStrategy
from backend.app.strategies.range_bound import RangeBoundStrategy


class AdaptiveStrategyEngine:
    """
    Coordinates regime-based strategy selection and execution.
    Can return WAIT or NO_TRADE whenever market conditions are unsuitable.
    """

    def __init__(self):
        self.trend_strategy = TrendFollowingStrategy()
        self.range_strategy = RangeBoundStrategy()
        self.registered_strategies: Dict[str, BaseStrategy] = {
            "trend_following": self.trend_strategy,
            "range_bound": self.range_strategy,
        }

    def evaluate_market(
        self,
        symbol: str,
        df_m15: pd.DataFrame,
        df_h1: Optional[pd.DataFrame] = None,
        current_spread_pips: float = 1.2
    ) -> SignalResult:
        """
        Evaluate full market pipeline:
        1. Calculate indicators
        2. Classify market regime
        3. Match eligible strategy candidate
        4. Produce schema-compliant signal
        """
        # Ensure indicators are calculated
        df_m15_ind = MarketDataService.calculate_indicators(df_m15)
        df_h1_ind = MarketDataService.calculate_indicators(df_h1) if df_h1 is not None else None

        regime, regime_details = MarketDataService.classify_regime(df_m15_ind)

        latest_close = float(df_m15_ind.iloc[-1]["close"]) if len(df_m15_ind) > 0 else 0.0

        # Unsuitable / High Volatility / Uncertain Regimes
        if regime == "high_volatility":
            return SignalResult(
                signal_type=SignalType.WAIT,
                symbol=symbol,
                strategy_name="regime_filter",
                entry_price=latest_close,
                stop_loss=0.0,
                take_profit=0.0,
                market_regime=regime,
                supporting_evidence=[],
                contradicting_evidence=["Market is experiencing elevated volatility and expanding ATR"],
                invalidation_conditions=[],
                reasoning_summary="Trading paused during high volatility / transition regime to protect capital."
            )

        if regime == "uncertain":
            return SignalResult(
                signal_type=SignalType.WAIT,
                symbol=symbol,
                strategy_name="regime_filter",
                entry_price=latest_close,
                stop_loss=0.0,
                take_profit=0.0,
                market_regime=regime,
                supporting_evidence=[],
                contradicting_evidence=["Directional indicators and momentum signals are in conflict"],
                invalidation_conditions=[],
                reasoning_summary="Market regime classified as uncertain; awaiting clear structural alignment."
            )

        # Trending Regime -> Evaluate Trend-Following Strategy
        if regime == "trending":
            sig = self.trend_strategy.evaluate(symbol, df_m15_ind, df_h1_ind, current_spread_pips)
            sig.market_regime = regime
            return sig

        # Ranging Regime -> Evaluate Range-Bound Strategy
        if regime == "ranging":
            sig = self.range_strategy.evaluate(symbol, df_m15_ind, df_h1_ind, current_spread_pips)
            sig.market_regime = regime
            return sig

        return SignalResult(
            signal_type=SignalType.WAIT,
            symbol=symbol,
            strategy_name="default",
            entry_price=latest_close,
            stop_loss=0.0,
            take_profit=0.0,
            market_regime="uncertain",
            reasoning_summary="No trade conditions met."
        )


# Global singleton instance of AdaptiveStrategyEngine
strategy_engine = AdaptiveStrategyEngine()
