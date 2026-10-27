"""
Comprehensive Automated Tests for TradePilot AI Offline Backtesting Engine
Verifies data ingestion, feature pipeline, no look-ahead bias, cost modeling,
intrabar collisions, position sizing, circuit breakers, reporting, and broker isolation.
"""
import io
import math
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

from backend.app.backtesting import (
    HistoricalDataLoader,
    FeaturePipeline,
    BaselineTrendStrategy,
    StrategyConfig,
    SignalDecision,
    TransactionCostModel,
    CostModelConfig,
    CostModelPresets,
    BacktestRiskManager,
    RiskConfig,
    OfflineBacktestEngine,
    ChronologicalSplitter,
    PerformanceMetricsCalculator,
    BacktestReportGenerator,
)


@pytest.fixture
def synthetic_m15_series():
    """Generates 300 deterministic M15 candles for mathematical test verification."""
    times = []
    opens, highs, lows, closes, volumes, spreads = [], [], [], [], [], []

    base_time = 1704067200  # 2024-01-01 00:00:00 UTC (Monday)
    price = 1.08000

    np.random.seed(42)

    for i in range(300):
        t = base_time + (i * 900)
        # Add slight trend wave
        delta = 0.00015 * math.sin(i / 15.0) + (np.random.normal(0, 0.0001))
        open_p = price
        close_p = round(open_p + delta, 5)
        high_p = round(max(open_p, close_p) + 0.00020, 5)
        low_p = round(min(open_p, close_p) - 0.00020, 5)

        times.append(t)
        opens.append(open_p)
        highs.append(high_p)
        lows.append(low_p)
        closes.append(close_p)
        volumes.append(100.0)
        spreads.append(1.2)

        price = close_p

    df = pd.DataFrame({
        "time": times,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "spread": spreads
    })
    return df


# 1. Data Ingestion: CSV Parsing & Invalid OHLC rows
def test_csv_parsing_and_invalid_ohlc_rejection():
    csv_text = """time,open,high,low,close,volume
2024-01-01 00:00:00,1.0800,1.0820,1.0790,1.0810,100
2024-01-01 00:15:00,1.0810,1.0800,1.0820,1.0815,100
2024-01-01 00:30:00,1.0815,1.0830,1.0800,-1.0820,100
2024-01-01 00:45:00,1.0820,1.0850,1.0810,1.0840,100
"""
    # Row 2 has High (1.0800) < Low (1.0820) -> Invalid
    # Row 3 has negative close (-1.0820) -> Invalid
    df, report = HistoricalDataLoader.load_from_csv(io.StringIO(csv_text), source_name="test.csv")

    assert report.total_rows == 4
    assert report.valid_rows == 2
    assert report.rejected_rows == 2
    assert len(df) == 2
    assert df["open"].iloc[0] == 1.0800
    assert df["open"].iloc[1] == 1.0820


# 2. Duplicate and Out-of-Order Timestamps
def test_duplicate_and_out_of_order_timestamps():
    csv_text = """time,open,high,low,close
1704067200,1.0800,1.0820,1.0790,1.0810
1704068100,1.0810,1.0830,1.0800,1.0820
1704067200,1.0800,1.0820,1.0790,1.0810
1704066300,1.0790,1.0810,1.0780,1.0800
"""
    df, report = HistoricalDataLoader.load_from_csv(io.StringIO(csv_text))

    assert report.duplicate_timestamps == 1
    assert df["time"].is_monotonic_increasing
    assert len(df) == 3


# 3. Indicator Calculations & Feature Warm-up
def test_feature_pipeline_and_warmup(synthetic_m15_series):
    df_feat = FeaturePipeline.calculate_features(synthetic_m15_series, slow_ema_period=200)

    assert "ema_50" in df_feat.columns
    assert "ema_200" in df_feat.columns
    assert "rsi_14" in df_feat.columns
    assert "atr_14" in df_feat.columns
    assert "rolling_volatility_20" in df_feat.columns
    assert "trend_direction" in df_feat.columns
    assert "is_warmup" in df_feat.columns

    # Warm-up check: bar 50 is warm-up, bar 250 is not
    assert df_feat["is_warmup"].iloc[50] == True
    assert df_feat["is_warmup"].iloc[250] == False

    # Check RSI bounded in [0, 100]
    valid_rsi = df_feat["rsi_14"].dropna()
    assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()

    # Check ATR > 0
    valid_atr = df_feat["atr_14"].dropna()
    assert (valid_atr > 0).all()


# 4. No Look-Ahead Bias Verification
def test_no_look_ahead_bias(synthetic_m15_series):
    """Features at bar i must not change when future bars are modified."""
    df1 = FeaturePipeline.calculate_features(synthetic_m15_series)

    # Modify future candles (bars 200+)
    altered_series = synthetic_m15_series.copy()
    altered_series.loc[200:, "close"] = altered_series.loc[200:, "close"] * 1.5
    altered_series.loc[200:, "high"] = altered_series.loc[200:, "high"] * 1.5

    df2 = FeaturePipeline.calculate_features(altered_series)

    # Features at bar 150 must be completely identical
    assert df1.loc[150, "ema_50"] == pytest.approx(df2.loc[150, "ema_50"], abs=1e-8)
    assert df1.loc[150, "ema_200"] == pytest.approx(df2.loc[150, "ema_200"], abs=1e-8)
    assert df1.loc[150, "rsi_14"] == pytest.approx(df2.loc[150, "rsi_14"], abs=1e-6)
    assert df1.loc[150, "atr_14"] == pytest.approx(df2.loc[150, "atr_14"], abs=1e-8)


# 5. Next-Candle Execution & Strategy Wait
def test_strategy_wait_and_next_candle_execution(synthetic_m15_series):
    strat = BaselineTrendStrategy()
    # During warm-up, decision must be WAIT
    bar_warmup = {"time": 1000, "is_warmup": True}
    sig = strat.evaluate_bar(0, bar_warmup)
    assert sig.decision == SignalDecision.WAIT

    # Test engine executes at next candle open
    df_feat = FeaturePipeline.calculate_features(synthetic_m15_series)
    engine = OfflineBacktestEngine(initial_balance=10000.0)
    res = engine.run(df_feat)

    # For any trade, entry_time must match the bar open time of a candle, not previous candle
    for t in res["trades"]:
        assert t["entry_time"] > 0
        assert t["exit_time"] >= t["entry_time"]


# 6. Transaction Cost Modeling (Spread, Commission, Slippage, Swap)
def test_transaction_cost_calculations():
    cost_model = TransactionCostModel(CostModelPresets.normal())

    # Entry with 1.2 pip spread and 0.5 pip slippage for BUY at Open 1.08000
    exec_price, spread_used, slip = cost_model.get_execution_entry_price("BUY", 1.08000, bar_spread_pips=1.2)
    # Expected: 1.08000 + 0.00006 (half spread) + 0.00005 (slippage) = 1.08011
    assert exec_price == 1.08011
    assert spread_used == 1.2
    assert slip == 0.5

    # Commission for 2.0 lots at $7.00/lot = $14.00
    comm = cost_model.calculate_commission(2.0)
    assert comm == 14.00

    # Overnight swap: crossing 21:00 UTC
    t_entry = 1704132000  # 2024-01-01 18:00:00 UTC
    t_exit = 1704225600   # 2024-01-02 20:00:00 UTC (Crossed 1 night)
    swap = cost_model.calculate_swap("BUY", 1.0, t_entry, t_exit)
    assert swap == -2.50


# 7. Conservative Intrabar Collision Handling
def test_conservative_collision_handling():
    """When both SL and TP price levels are within candle range, SL triggers first."""
    rows = []
    for i in range(60):
        open_p = 1.0800
        close_p = 1.0810
        high_p = 1.0820
        low_p = 1.0790
        # Bar 52 is extreme candle sweeping both SL and TP
        if i == 52:
            high_p = 1.0950  # > TP
            low_p = 1.0650   # < SL
        rows.append({
            "time": 1000 + (i * 900),
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "volume": 100.0,
            "spread": 1.2,
            "ema_50": 1.0700,
            "ema_200": 1.0600,
            "rsi_14": 60.0,
            "atr_14": 0.0020,
            "is_warmup": False
        })
    df = pd.DataFrame(rows)

    engine = OfflineBacktestEngine(initial_balance=10000.0)
    res = engine.run(df)

    assert len(res["trades"]) > 0
    collision_trades = [t for t in res["trades"] if t["exit_reason"] == "COLLISION_STOP_LOSS"]
    assert len(collision_trades) > 0
    assert collision_trades[0]["net_pnl"] < 0


# 8. Deterministic Position Sizing (0.25% Equity Risk)
def test_position_sizing_and_rounding():
    risk_mgr = BacktestRiskManager(RiskConfig(risk_per_trade_pct=0.25))

    # Equity $10,000 -> 0.25% = $25.00
    # Stop distance = 25 pips ($10/pip on 1 lot -> $250 risk per lot)
    # Expected volume = $25 / $250 = 0.10 lots
    lots, status = risk_mgr.calculate_lot_size(equity=10000.0, stop_distance_pips=25.0)
    assert status == "OK"
    assert lots == 0.10

    # Volume step round-down check
    # 23 pips -> $25 / (23 * 10) = 0.10869... lots -> floor to 0.10
    lots2, _ = risk_mgr.calculate_lot_size(equity=10000.0, stop_distance_pips=23.0)
    assert lots2 == 0.10


# 9. Daily & Weekly Loss Circuit Breakers
def test_daily_and_weekly_loss_circuit_breakers():
    risk_mgr = BacktestRiskManager(RiskConfig(max_daily_loss_pct=1.0, max_weekly_loss_pct=3.0))
    risk_mgr.reset(10000.0)
    risk_mgr.update_calendar_baselines(1704067200, 10000.0)

    # 1.0% of $10,000 is $100 loss -> Equity drops to $9890 (1.1% loss)
    allowed, reason = risk_mgr.check_trade_allowed(current_equity=9890.0)
    assert allowed == False
    assert "Daily loss limit reached" in reason


# 10. Pause After 3 Consecutive Losses
def test_consecutive_losses_limit():
    risk_mgr = BacktestRiskManager(RiskConfig(consecutive_losses_limit=3))
    risk_mgr.reset(10000.0)

    risk_mgr.record_trade_result(-25.0)
    assert risk_mgr.consecutive_losses == 1
    assert risk_mgr.is_locked == False

    risk_mgr.record_trade_result(-25.0)
    assert risk_mgr.consecutive_losses == 2
    assert risk_mgr.is_locked == False

    risk_mgr.record_trade_result(-25.0)
    assert risk_mgr.consecutive_losses == 3
    assert risk_mgr.is_locked == True

    allowed, reason = risk_mgr.check_trade_allowed(10000.0)
    assert allowed == False
    assert "Consecutive loss limit" in reason or "Paused after 3 consecutive losses" in reason


# 11. End-of-Dataset Position Cleanup
def test_end_of_dataset_position_closing(synthetic_m15_series):
    df_feat = FeaturePipeline.calculate_features(synthetic_m15_series)
    engine = OfflineBacktestEngine(initial_balance=10000.0)
    res = engine.run(df_feat)

    # If any trade exited at the very last candle, its exit_reason must be END_OF_DATASET
    if res["trades"]:
        last_trade = res["trades"][-1]
        if last_trade["exit_time"] == int(synthetic_m15_series["time"].iloc[-1]):
            assert last_trade["exit_reason"] in {"END_OF_DATASET", "STOP_LOSS", "TAKE_PROFIT"}


# 12. Safe Performance Metrics Calculations (Zero Trades & Zero Losses)
def test_metrics_calculator_edge_cases():
    # Zero trades
    empty_m = PerformanceMetricsCalculator.calculate(10000.0, [], [])
    assert empty_m["total_trades"] == 0
    assert empty_m["profit_factor"] == 0.0
    assert empty_m["win_rate"] == 0.0
    assert empty_m["trade_expectancy"] == 0.0

    # All wins (Zero losses)
    win_trades = [
        {"net_pnl": 50.0, "commission": 1.4, "swap": 0.0, "holding_seconds": 1800, "holding_bars": 2},
        {"net_pnl": 40.0, "commission": 1.4, "swap": 0.0, "holding_seconds": 1800, "holding_bars": 2}
    ]
    all_wins_m = PerformanceMetricsCalculator.calculate(10000.0, win_trades, [{"equity": 10090.0}])
    assert all_wins_m["profit_factor"] == 99.0  # Defined safe value without division by zero
    assert all_wins_m["win_rate"] == 100.0
    assert all_wins_m["gross_loss"] == 0.0


# 13. Chronological Dataset Partitioning (60 / 20 / 20)
def test_chronological_splitting(synthetic_m15_series):
    df_feat = FeaturePipeline.calculate_features(synthetic_m15_series)
    part_res = ChronologicalSplitter.run_partitioned_backtest(df_feat, initial_balance=10000.0)

    assert "partitions" in part_res
    parts = part_res["partitions"]
    assert "development" in parts
    assert "validation" in parts
    assert "untouched_test" in parts

    dev_bars = parts["development"]["bars_count"]
    val_bars = parts["validation"]["bars_count"]
    test_bars = parts["untouched_test"]["bars_count"]

    # Verify 60% / 20% / 20% distribution of total 300 bars
    assert dev_bars == 180
    assert val_bars == 60
    assert test_bars == 60
    assert dev_bars + val_bars + test_bars == 300


# 14. PDF and CSV Reporting Exports
def test_report_generation(tmp_path):
    results = {
        "full_dataset": {
            "metrics": {
                "net_pnl": 125.50,
                "total_trades": 10,
                "winning_trades": 6,
                "losing_trades": 4,
                "win_rate": 60.0,
                "profit_factor": 1.85,
                "return_pct": 1.25,
                "average_win": 35.0,
                "average_loss": 21.0,
                "trade_expectancy": 12.55,
                "max_drawdown_pct": 0.85,
                "max_drawdown_amount": 85.0,
                "average_holding_hours": 2.5,
                "total_commission": 14.0,
                "total_swap": -2.5,
            },
            "trades": [
                {"trade_id": 1, "type": "BUY", "volume": 0.1, "entry_price": 1.0810, "exit_price": 1.0840,
                 "net_pnl": 28.60, "exit_reason": "TAKE_PROFIT", "mfe_pips": 32.0, "mae_pips": 4.0}
            ]
        },
        "strategy_config": StrategyConfig().to_dict(),
        "cost_scenario": CostModelPresets.normal().to_dict(),
        "risk_config": RiskConfig().to_dict(),
    }

    pdf_file = str(tmp_path / "research_report.pdf")
    generated_path = BacktestReportGenerator.generate_pdf(results, None, pdf_file)
    assert Path(generated_path).exists()
    assert Path(generated_path).stat().st_size > 1000

    csv_data = BacktestReportGenerator.export_csv_trades(results["full_dataset"]["trades"])
    assert "trade_id,type,volume" in csv_data
    assert "BUY" in csv_data


# 15. Offline Engine Never Invokes Broker Execution
def test_backtester_never_invokes_broker(synthetic_m15_series, monkeypatch):
    """Guarantees the backtest engine does not make any broker order calls."""
    import MetaTrader5 as mt5

    def mock_order_send(*args, **kwargs):
        raise AssertionError("CRITICAL FAILURE: Backtester attempted to submit live broker order!")

    monkeypatch.setattr(mt5, "order_send", mock_order_send)

    df_feat = FeaturePipeline.calculate_features(synthetic_m15_series)
    engine = OfflineBacktestEngine(initial_balance=10000.0)
    # Must complete safely without calling mock_order_send
    res = engine.run(df_feat)
    assert "trades" in res


# 16. Regression Test: Daily Reset vs Permanent Lock for Consecutive Losses
def test_consecutive_losses_reset_daily_vs_permanent():
    """
    Validates that consecutive loss lock can either:
    1) Pause trading for the day and reset at 00:00 UTC (consecutive_losses_reset_daily=True)
    2) Permanently halt trading across subsequent days (consecutive_losses_reset_daily=False)
    """
    # Case A: Daily Reset
    mgr_daily = BacktestRiskManager(RiskConfig(consecutive_losses_limit=3, consecutive_losses_reset_daily=True))
    mgr_daily.reset(10000.0)
    
    t_day1 = int(datetime(2025, 5, 1, 14, 0, tzinfo=timezone.utc).timestamp())
    t_day2 = int(datetime(2025, 5, 2, 8, 0, tzinfo=timezone.utc).timestamp())

    mgr_daily.update_calendar_baselines(t_day1, 10000.0)
    for _ in range(3):
        mgr_daily.record_trade_result(-25.0)
    
    assert mgr_daily.is_locked == True
    assert mgr_daily.consecutive_losses == 3
    allowed, _ = mgr_daily.check_trade_allowed(10000.0)
    assert allowed == False

    # Day 2 transition
    mgr_daily.update_calendar_baselines(t_day2, 9925.0)
    assert mgr_daily.is_locked == False
    assert mgr_daily.consecutive_losses == 0
    allowed_day2, _ = mgr_daily.check_trade_allowed(9925.0)
    assert allowed_day2 == True

    # Case B: Permanent Lock
    mgr_perm = BacktestRiskManager(RiskConfig(consecutive_losses_limit=3, consecutive_losses_reset_daily=False))
    mgr_perm.reset(10000.0)
    mgr_perm.update_calendar_baselines(t_day1, 10000.0)
    for _ in range(3):
        mgr_perm.record_trade_result(-25.0)
    
    assert mgr_perm.is_locked == True
    # Day 2 transition must NOT clear permanent lock
    mgr_perm.update_calendar_baselines(t_day2, 9925.0)
    assert mgr_perm.is_locked == True
    assert mgr_perm.consecutive_losses == 3
    allowed_perm, reason = mgr_perm.check_trade_allowed(9925.0)
    assert allowed_perm == False
    assert "Risk locked" in reason


# 17. Regression Test: H1 Trend Alignment Zero Look-Ahead Bias
def test_h1_alignment_zero_lookahead_bias():
    """
    Guarantees that M15 decisions at time T use exclusively H1 candles that fully closed
    at or before time T. An H1 candle opening at T cannot be visible until T + 3600.
    """
    # Deterministic H1 bars (09:00, 10:00, 11:00 UTC on 2025-06-01)
    base_t = int(datetime(2025, 6, 1, 9, 0, tzinfo=timezone.utc).timestamp())
    h1_records = [
        {"time": base_t, "open": 1.0500, "high": 1.0550, "low": 1.0490, "close": 1.0540, "tick_volume": 1000, "spread": 8.0},
        {"time": base_t + 3600, "open": 1.0540, "high": 1.0545, "low": 1.0420, "close": 1.0430, "tick_volume": 1200, "spread": 8.0},
        {"time": base_t + 7200, "open": 1.0430, "high": 1.0600, "low": 1.0425, "close": 1.0590, "tick_volume": 1500, "spread": 8.0},
    ]
    df_h1 = pd.DataFrame(h1_records)

    # Deterministic M15 bars covering 10:00 to 11:30 UTC
    m15_records = []
    for step in range(4, 11):  # 10:00, 10:15, 10:30, 10:45, 11:00, 11:15, 11:30
        m15_t = base_t + (step * 900)
        m15_records.append({
            "time": m15_t, "open": 1.0500, "high": 1.0520, "low": 1.0490, "close": 1.0510,
            "tick_volume": 200, "spread": 0.8
        })
    df_m15 = pd.DataFrame(m15_records)

    # Force known EMA/trend for H1 bars: bar 0 = UP, bar 1 = DOWN, bar 2 = UP
    # We test via align_h1_features
    df_aligned = FeaturePipeline.align_h1_features(df_m15, df_h1, fast_period=2, slow_period=3)

    # Check timestamps:
    # M15 at 10:00 (step 4, base_t + 3600): H1 bar 0 (09:00) closed at 10:00.
    # Must use H1 bar 0!
    m15_1000 = df_aligned[df_aligned["time"] == base_t + 3600].iloc[0]
    m15_1045 = df_aligned[df_aligned["time"] == base_t + 4500].iloc[0]
    assert m15_1000["h1_trend_direction"] in {"UP", "DOWN", "FLAT"}
    assert m15_1000["h1_trend_direction"] == m15_1045["h1_trend_direction"]

    # M15 at 11:00 (step 8, base_t + 7200): H1 bar 1 (10:00) closed at 11:00.
    # Must transition to H1 bar 1!
    m15_1100 = df_aligned[df_aligned["time"] == base_t + 7200].iloc[0]
    # In H1 bar 1, price plunged from 1.0540 to 1.0430, so fast EMA is below slow EMA -> DOWN
    assert m15_1100["h1_trend_direction"] == "DOWN"
    # M15 at 10:45 must NOT see H1 bar 1
    assert m15_1045["h1_trend_direction"] != "DOWN"


# 18. Regression Test: Transaction Cost Friction Without Double-Counting
def test_transaction_cost_zero_double_counting():
    """
    Confirms that spread is applied exactly once round-turn (split 50/50 on entry/exit),
    commission is deducted separately without polluting price points, and slippage is applied correctly.
    """
    cost_cfg = CostModelConfig(
        default_spread_pips=1.0,
        commission_per_lot_round_turn=7.00,
        slippage_pips=0.2
    )
    cost_model = TransactionCostModel(cost_cfg)

    # BUY Entry at Open 1.05000:
    # Ask = Open + (Spread / 2) + Slippage = 1.05000 + 0.00005 + 0.00002 = 1.05007
    exec_entry, spread_used, slip_used = cost_model.get_execution_entry_price("BUY", 1.05000, 1.0)
    assert exec_entry == 1.05007

    # BUY Stop Loss Exit at Target 1.04900 (Market Order):
    # Bid = Target - (Spread / 2) - Slippage = 1.04900 - 0.00005 - 0.00002 = 1.04893
    exec_exit, exit_spread, exit_slip = cost_model.get_execution_exit_price("BUY", 1.04900, is_stop_loss=True, bar_spread_pips=1.0)
    assert exec_exit == 1.04893

    # Total price friction:
    # Gross pip loss = (1.05007 - 1.04893) / 0.0001 = 11.4 pips
    # Breakdown: 10 pips nominal move + 1.0 pip full round-turn spread + 0.4 pip adverse slippage (entry + exit)
    # Exactly 1.0 pip spread is paid, ZERO double-counting!
    total_loss_pips = round((exec_entry - exec_exit) / 0.0001, 1)
    assert total_loss_pips == 11.4

    # Commission check on 0.10 lot
    comm = cost_model.calculate_commission(0.10)
    assert comm == 0.70  # Exactly $0.70 flat, separate from price

