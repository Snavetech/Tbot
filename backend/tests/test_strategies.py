"""
Unit tests for Adaptive Strategy Engine and Strategy Modules
"""
import pytest
import pandas as pd
from backend.app.strategies.engine import AdaptiveStrategyEngine
from backend.app.strategies.trend_following import TrendFollowingStrategy
from backend.app.strategies.range_bound import RangeBoundStrategy
from backend.app.strategies.base import SignalType
from backend.app.services.market_data import MarketDataService


def test_strategy_returns_wait_on_insufficient_data():
    """Strategy must return WAIT when not enough candles are available"""
    strat = TrendFollowingStrategy()
    df_empty = pd.DataFrame()
    signal = strat.evaluate("EURUSD", df_empty)
    assert signal.signal_type == SignalType.WAIT


def test_adaptive_engine_high_volatility_filter(sample_eurusd_candles):
    """Engine must return WAIT when volatility is extreme to protect capital"""
    engine = AdaptiveStrategyEngine()

    df = sample_eurusd_candles.copy()
    # Inject wide ATR / volatility spike
    df_ind = MarketDataService.calculate_indicators(df)
    df_ind.loc[df_ind.index[-1], "atr"] = 0.0090  # Huge ATR spike

    # Market data service will classify as high_volatility
    regime, _ = MarketDataService.classify_regime(df_ind)
    assert regime in {"high_volatility", "uncertain"}

    sig = engine.evaluate_market("EURUSD", df_ind)
    assert sig.signal_type == SignalType.WAIT


def test_range_strategy_disables_on_breakout(sample_eurusd_candles):
    """Range strategy disables when Bollinger Bands expand (breakout condition)"""
    strat = RangeBoundStrategy()
    df_ind = MarketDataService.calculate_indicators(sample_eurusd_candles.copy())

    # Simulate wide BB width (breakout condition)
    df_ind.loc[df_ind.index[-1], "bb_width"] = 0.0150

    signal = strat.evaluate("EURUSD", df_ind)
    assert signal.signal_type == SignalType.WAIT
    assert "disabled" in signal.reasoning_summary.lower()
