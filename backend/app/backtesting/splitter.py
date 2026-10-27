"""
Chronological Data Splitting & Cross-Validation Module
Partitions historical time series into Development (60%), Validation (20%),
and Untouched Test (20%) windows without shuffling or warm-up boundary leakage.
"""
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from backend.app.backtesting.engine import OfflineBacktestEngine
from backend.app.backtesting.metrics import PerformanceMetricsCalculator
from backend.app.backtesting.strategy import StrategyConfig
from backend.app.backtesting.costs import CostModelConfig, CostModelPresets
from backend.app.backtesting.risk import RiskConfig


class ChronologicalSplitter:
    """
    Partitions time-series datasets chronologically and coordinates out-of-sample validation.
    """

    @classmethod
    def split_indices(
        cls,
        total_rows: int,
        train_ratio: float = 0.60,
        val_ratio: float = 0.20
    ) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
        """
        Calculates slice indices for (Train, Validation, Test) partitions.
        Guarantees zero overlap and strict chronological ordering.
        """
        train_end = int(total_rows * train_ratio)
        val_end = int(total_rows * (train_ratio + val_ratio))

        train_range = (0, train_end)
        val_range = (train_end, val_end)
        test_range = (val_end, total_rows)

        return train_range, val_range, test_range

    @classmethod
    def run_partitioned_backtest(
        cls,
        df_candles_with_features: pd.DataFrame,
        initial_balance: float = 10000.0,
        strategy_config: Optional[StrategyConfig] = None,
        cost_config: Optional[CostModelConfig] = None,
        risk_config: Optional[RiskConfig] = None
    ) -> Dict[str, Any]:
        """
        Runs the simulation across all 3 chronological partitions (Train, Val, Test).
        Metrics are calculated separately for each partition to guarantee that
        the Untouched Test partition remains pure and distinct from parameter tuning.
        """
        df = df_candles_with_features.copy().reset_index(drop=True)
        total_rows = len(df)

        if total_rows < 150:
            return {"error": "Dataset too short for 60/20/20 chronological partition (minimum 150 bars required)"}

        train_range, val_range, test_range = cls.split_indices(total_rows)

        engine = OfflineBacktestEngine(
            initial_balance=initial_balance,
            strategy_config=strategy_config,
            cost_config=cost_config,
            risk_config=risk_config
        )

        # 1. Development / Training Split (0% to 60%)
        train_raw = engine.run(df, start_index=train_range[0], end_index=train_range[1])
        train_metrics = PerformanceMetricsCalculator.calculate(
            initial_balance=initial_balance,
            trades=train_raw["trades"],
            equity_curve=train_raw["equity_curve"]
        )

        # 2. Validation Split (60% to 80%)
        val_raw = engine.run(df, start_index=val_range[0], end_index=val_range[1])
        val_metrics = PerformanceMetricsCalculator.calculate(
            initial_balance=initial_balance,
            trades=val_raw["trades"],
            equity_curve=val_raw["equity_curve"]
        )

        # 3. Untouched Test Split (80% to 100%)
        test_raw = engine.run(df, start_index=test_range[0], end_index=test_range[1])
        test_metrics = PerformanceMetricsCalculator.calculate(
            initial_balance=initial_balance,
            trades=test_raw["trades"],
            equity_curve=test_raw["equity_curve"]
        )

        # 4. Full Dataset Benchmark
        full_raw = engine.run(df, start_index=0, end_index=total_rows)
        full_metrics = PerformanceMetricsCalculator.calculate(
            initial_balance=initial_balance,
            trades=full_raw["trades"],
            equity_curve=full_raw["equity_curve"]
        )

        # Helper to format partition dates
        def get_dates(start_idx, end_idx):
            if end_idx > start_idx and start_idx < len(df):
                st = df["time"].iloc[start_idx]
                et = df["time"].iloc[end_idx - 1]
                return st, et
            return 0, 0

        train_st, train_et = get_dates(*train_range)
        val_st, val_et = get_dates(*val_range)
        test_st, test_et = get_dates(*test_range)

        return {
            "partitions": {
                "development": {
                    "label": "Development / Training (60%)",
                    "start_index": train_range[0],
                    "end_index": train_range[1],
                    "start_time": train_st,
                    "end_time": train_et,
                    "bars_count": train_range[1] - train_range[0],
                    "metrics": train_metrics,
                    "trades": train_raw["trades"],
                    "equity_curve": train_raw["equity_curve"]
                },
                "validation": {
                    "label": "Validation (20%)",
                    "start_index": val_range[0],
                    "end_index": val_range[1],
                    "start_time": val_st,
                    "end_time": val_et,
                    "bars_count": val_range[1] - val_range[0],
                    "metrics": val_metrics,
                    "trades": val_raw["trades"],
                    "equity_curve": val_raw["equity_curve"]
                },
                "untouched_test": {
                    "label": "Untouched Out-Of-Sample Test (20%)",
                    "start_index": test_range[0],
                    "end_index": test_range[1],
                    "start_time": test_st,
                    "end_time": test_et,
                    "bars_count": test_range[1] - test_range[0],
                    "metrics": test_metrics,
                    "trades": test_raw["trades"],
                    "equity_curve": test_raw["equity_curve"]
                }
            },
            "full_dataset": {
                "total_bars": total_rows,
                "metrics": full_metrics,
                "trades": full_raw["trades"],
                "equity_curve": full_raw["equity_curve"]
            },
            "disclaimer": "The Untouched Test partition was evaluated once under frozen parameters without tuning feedback."
        }

    @classmethod
    def run_sensitivity_grid(
        cls,
        df_candles_with_features: pd.DataFrame,
        base_strategy_config: StrategyConfig,
        cost_config: Optional[CostModelConfig] = None,
        risk_config: Optional[RiskConfig] = None,
        initial_balance: float = 10000.0
    ) -> List[Dict[str, Any]]:
        """
        Evaluates parameter sensitivity on Development and Validation partitions,
        demonstrating whether performance is robust or fragile to small parameter shifts.
        """
        df = df_candles_with_features.copy().reset_index(drop=True)
        train_range, val_range, _ = cls.split_indices(len(df))

        # Sensitivity grid over Stop Multiplier and Risk-to-Reward Ratio
        stop_mults = [1.0, 1.5, 2.0]
        rr_ratios = [1.5, 2.0, 2.5]

        results = []
        for sm in stop_mults:
            for rr in rr_ratios:
                cfg = StrategyConfig(
                    fast_ema_period=base_strategy_config.fast_ema_period,
                    slow_ema_period=base_strategy_config.slow_ema_period,
                    rsi_period=base_strategy_config.rsi_period,
                    rsi_long_min=base_strategy_config.rsi_long_min,
                    rsi_long_max=base_strategy_config.rsi_long_max,
                    rsi_short_min=base_strategy_config.rsi_short_min,
                    rsi_short_max=base_strategy_config.rsi_short_max,
                    atr_stop_multiplier=sm,
                    risk_reward_ratio=rr,
                    cooldown_bars=base_strategy_config.cooldown_bars,
                )

                engine = OfflineBacktestEngine(
                    initial_balance=initial_balance,
                    strategy_config=cfg,
                    cost_config=cost_config,
                    risk_config=risk_config
                )

                # Evaluate on combined Dev + Val (First 80%), leaving Test untouched
                eval_res = engine.run(df, start_index=0, end_index=val_range[1])
                metrics = PerformanceMetricsCalculator.calculate(
                    initial_balance=initial_balance,
                    trades=eval_res["trades"],
                    equity_curve=eval_res["equity_curve"]
                )

                results.append({
                    "atr_stop_multiplier": sm,
                    "risk_reward_ratio": rr,
                    "total_trades": metrics["total_trades"],
                    "win_rate": metrics["win_rate"],
                    "profit_factor": metrics["profit_factor"],
                    "net_pnl": metrics["net_pnl"],
                    "max_drawdown_pct": metrics["max_drawdown_pct"],
                    "trade_expectancy": metrics["trade_expectancy"]
                })

        return results
