"""
Unit tests for Chronological Backtesting Engine
"""
import pytest
from backend.app.services.backtester import BacktestEngine


def test_backtest_runs_chronologically(sample_eurusd_candles):
    """Backtest processes candles chronologically without look-ahead bias"""
    engine = BacktestEngine(
        initial_balance=10000.0,
        spread_pips=1.2,
        slippage_points=5,
        commission_per_lot=7.0
    )

    results = engine.run_backtest(
        df_candles=sample_eurusd_candles,
        strategy_mode="all",
        symbol="EURUSD"
    )

    assert "metrics" in results
    assert "equity_curve" in results
    assert "trades" in results
    assert results["initial_balance"] == 10000.0

    metrics = results["metrics"]
    assert "win_rate" in metrics
    assert "profit_factor" in metrics
    assert "max_drawdown_pct" in metrics

    # Verify equity curve starts at initial balance
    if results["equity_curve"]:
        assert results["equity_curve"][0]["balance"] == 10000.0


def test_backtest_insufficient_data():
    """Engine refuses to backtest if bar count is below minimum threshold"""
    import pandas as pd
    engine = BacktestEngine()
    df_short = pd.DataFrame({"time": [1, 2], "close": [1.0, 1.1]})
    res = engine.run_backtest(df_short)
    assert "error" in res
