"""
Event-Driven Chronological Simulation Engine
Simulates historical Forex trading bar-by-bar with zero look-ahead bias,
explicit transaction friction, conservative intrabar collision handling,
and separate balance/equity accounting.
"""
from typing import Dict, Any, List, Optional
import math
import pandas as pd
import numpy as np

from backend.app.backtesting.strategy import BaselineTrendStrategy, StrategyConfig, SignalDecision
from backend.app.backtesting.costs import TransactionCostModel, CostModelConfig, CostModelPresets
from backend.app.backtesting.risk import BacktestRiskManager, RiskConfig


class OfflineBacktestEngine:
    """
    Chronological bar-by-bar backtesting simulation engine.
    Completely isolated from live or demo broker connections.
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        strategy_config: Optional[StrategyConfig] = None,
        cost_config: Optional[CostModelConfig] = None,
        risk_config: Optional[RiskConfig] = None
    ):
        self.initial_balance = initial_balance
        self.strategy = BaselineTrendStrategy(config=strategy_config)
        self.cost_model = TransactionCostModel(config=cost_config or CostModelPresets.normal())
        self.risk_manager = BacktestRiskManager(config=risk_config)

    def run(
        self,
        df_candles: pd.DataFrame,
        start_index: Optional[int] = None,
        end_index: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes chronological simulation over candlestick DataFrame.
        Optional start_index and end_index allow running on specific split partitions.
        """
        if len(df_candles) < 50:
            return {
                "error": "Insufficient candle data (minimum 50 bars required)",
                "trades": [],
                "equity_curve": []
            }

        df = df_candles.copy().reset_index(drop=True)
        total_len = len(df)

        # Partition indices
        start_i = max(0, start_index) if start_index is not None else 0
        end_i = min(total_len, end_index) if end_index is not None else total_len

        # State initialization
        balance = self.initial_balance
        equity = self.initial_balance
        peak_equity = self.initial_balance

        self.risk_manager.reset(initial_equity=self.initial_balance)

        open_position: Optional[Dict[str, Any]] = None
        pending_order: Optional[Dict[str, Any]] = None
        trades: List[Dict[str, Any]] = []
        equity_curve: List[Dict[str, Any]] = []

        bars_since_last_exit = 9999

        # Chronological Bar-by-Bar Loop
        for i in range(start_i, end_i):
            bar = df.iloc[i]
            bar_time = int(bar["time"])
            open_p = float(bar["open"])
            high_p = float(bar["high"])
            low_p = float(bar["low"])
            close_p = float(bar["close"])
            spread = float(bar.get("spread", self.cost_model.config.default_spread_pips))

            # 1. Update calendar risk baselines (daily and weekly equity baselines)
            self.risk_manager.update_calendar_baselines(bar_time, current_equity=equity)

            # 2. Execute Pending Order at Current Candle's OPEN (Next-Candle Execution)
            if pending_order is not None and open_position is None:
                sig_type = pending_order["type"]
                stop_dist = pending_order["stop_distance_pips"]
                target_dist = pending_order["target_distance_pips"]

                # Apply spread and slippage to entry price
                exec_price, spread_used, slip_pips = self.cost_model.get_execution_entry_price(
                    position_type=sig_type,
                    candle_open_price=open_p,
                    bar_spread_pips=spread
                )

                # Calculate lot size
                lot_size, size_reason = self.risk_manager.calculate_lot_size(
                    equity=equity,
                    stop_distance_pips=stop_dist
                )

                if lot_size > 0:
                    # Calculate price levels
                    if sig_type == "BUY":
                        sl_price = round(exec_price - (stop_dist * 0.0001), 5)
                        tp_price = round(exec_price + (target_dist * 0.0001), 5)
                    else:
                        sl_price = round(exec_price + (stop_dist * 0.0001), 5)
                        tp_price = round(exec_price - (target_dist * 0.0001), 5)

                    open_position = {
                        "trade_id": len(trades) + 1,
                        "type": sig_type,
                        "volume": lot_size,
                        "entry_bar": i,
                        "entry_time": bar_time,
                        "entry_price": exec_price,
                        "sl": sl_price,
                        "tp": tp_price,
                        "reason": pending_order["reason"],
                        "entry_spread": spread_used,
                        "entry_slippage": slip_pips,
                        "mfe_price": exec_price,  # Max favorable excursion
                        "mae_price": exec_price,  # Max adverse excursion
                    }
                pending_order = None

            # 3. Manage Open Position (Intrabar SL / TP evaluation on current bar)
            if open_position is not None:
                pos_type = open_position["type"]
                entry_p = open_position["entry_price"]
                sl = open_position["sl"]
                tp = open_position["tp"]
                vol = open_position["volume"]

                # Track MFE / MAE
                if pos_type == "BUY":
                    open_position["mfe_price"] = max(open_position["mfe_price"], high_p)
                    open_position["mae_price"] = min(open_position["mae_price"], low_p)
                else:
                    open_position["mfe_price"] = min(open_position["mfe_price"], low_p)
                    open_position["mae_price"] = max(open_position["mae_price"], high_p)

                exit_price = None
                exit_reason = None
                is_stop_loss = False

                # Evaluate Intrabar Collision & Triggers
                if pos_type == "BUY":
                    sl_hit = low_p <= sl
                    tp_hit = high_p >= tp

                    if sl_hit and tp_hit:
                        # CONSERVATIVE COLLISION HANDLING:
                        # If both SL and TP are touched in the same bar, assume SL triggered first!
                        exit_price = sl
                        exit_reason = "COLLISION_STOP_LOSS"
                        is_stop_loss = True
                    elif sl_hit:
                        exit_price = sl
                        exit_reason = "STOP_LOSS"
                        is_stop_loss = True
                    elif tp_hit:
                        exit_price = tp
                        exit_reason = "TAKE_PROFIT"
                        is_stop_loss = False
                else:  # SELL
                    sl_hit = high_p >= sl
                    tp_hit = low_p <= tp

                    if sl_hit and tp_hit:
                        exit_price = sl
                        exit_reason = "COLLISION_STOP_LOSS"
                        is_stop_loss = True
                    elif sl_hit:
                        exit_price = sl
                        exit_reason = "STOP_LOSS"
                        is_stop_loss = True
                    elif tp_hit:
                        exit_price = tp
                        exit_reason = "TAKE_PROFIT"
                        is_stop_loss = False

                if exit_price is not None:
                    # Finalize trade exit with friction
                    final_exit, exit_spread, exit_slip = self.cost_model.get_execution_exit_price(
                        position_type=pos_type,
                        target_price=exit_price,
                        is_stop_loss=is_stop_loss,
                        bar_spread_pips=spread
                    )

                    pip_diff = (
                        (final_exit - entry_p) / 0.0001
                        if pos_type == "BUY"
                        else (entry_p - final_exit) / 0.0001
                    )
                    gross_pnl = round(pip_diff * 10.0 * vol, 2)
                    commission = self.cost_model.calculate_commission(vol)
                    swap = self.cost_model.calculate_swap(
                        position_type=pos_type,
                        volume_lots=vol,
                        entry_timestamp=open_position["entry_time"],
                        exit_timestamp=bar_time
                    )
                    net_pnl = round(gross_pnl - commission + swap, 2)

                    balance += net_pnl
                    equity = balance

                    holding_bars = i - open_position["entry_bar"]
                    holding_duration_seconds = bar_time - open_position["entry_time"]

                    # Calculate MFE / MAE in pips
                    if pos_type == "BUY":
                        mfe_pips = round((open_position["mfe_price"] - entry_p) / 0.0001, 1)
                        mae_pips = round((entry_p - open_position["mae_price"]) / 0.0001, 1)
                    else:
                        mfe_pips = round((entry_p - open_position["mfe_price"]) / 0.0001, 1)
                        mae_pips = round((open_position["mae_price"] - entry_p) / 0.0001, 1)

                    trade_record = {
                        "trade_id": open_position["trade_id"],
                        "type": pos_type,
                        "volume": vol,
                        "entry_time": open_position["entry_time"],
                        "exit_time": bar_time,
                        "entry_price": entry_p,
                        "exit_price": final_exit,
                        "sl": sl,
                        "tp": tp,
                        "gross_pnl": gross_pnl,
                        "commission": commission,
                        "swap": swap,
                        "net_pnl": net_pnl,
                        "exit_reason": exit_reason,
                        "holding_bars": holding_bars,
                        "holding_seconds": holding_duration_seconds,
                        "mfe_pips": max(0.0, mfe_pips),
                        "mae_pips": max(0.0, mae_pips),
                        "entry_spread_pips": open_position["entry_spread"],
                        "exit_spread_pips": exit_spread,
                        "slippage_pips": open_position["entry_slippage"] + exit_slip,
                    }
                    trades.append(trade_record)
                    self.risk_manager.record_trade_result(net_pnl)

                    open_position = None
                    bars_since_last_exit = 0
                else:
                    bars_since_last_exit += 1
            else:
                bars_since_last_exit += 1

            # 4. Handle End-of-Dataset: Mark open position to market and close cleanly
            if i == end_i - 1 and open_position is not None:
                pos_type = open_position["type"]
                entry_p = open_position["entry_price"]
                vol = open_position["volume"]

                final_exit, exit_spread, exit_slip = self.cost_model.get_execution_exit_price(
                    position_type=pos_type,
                    target_price=close_p,
                    is_stop_loss=True,
                    bar_spread_pips=spread
                )

                pip_diff = (
                    (final_exit - entry_p) / 0.0001
                    if pos_type == "BUY"
                    else (entry_p - final_exit) / 0.0001
                )
                gross_pnl = round(pip_diff * 10.0 * vol, 2)
                commission = self.cost_model.calculate_commission(vol)
                swap = self.cost_model.calculate_swap(
                    position_type=pos_type,
                    volume_lots=vol,
                    entry_timestamp=open_position["entry_time"],
                    exit_timestamp=bar_time
                )
                net_pnl = round(gross_pnl - commission + swap, 2)

                balance += net_pnl
                equity = balance

                trades.append({
                    "trade_id": open_position["trade_id"],
                    "type": pos_type,
                    "volume": vol,
                    "entry_time": open_position["entry_time"],
                    "exit_time": bar_time,
                    "entry_price": entry_p,
                    "exit_price": final_exit,
                    "sl": open_position["sl"],
                    "tp": open_position["tp"],
                    "gross_pnl": gross_pnl,
                    "commission": commission,
                    "swap": swap,
                    "net_pnl": net_pnl,
                    "exit_reason": "END_OF_DATASET",
                    "holding_bars": i - open_position["entry_bar"],
                    "holding_seconds": bar_time - open_position["entry_time"],
                    "mfe_pips": 0.0,
                    "mae_pips": 0.0,
                    "entry_spread_pips": open_position["entry_spread"],
                    "exit_spread_pips": exit_spread,
                    "slippage_pips": open_position["entry_slippage"] + exit_slip,
                })
                self.risk_manager.record_trade_result(net_pnl)
                open_position = None

            # 5. Evaluate Strategy Signals at End of Candle (For next candle execution)
            if open_position is None and pending_order is None:
                # Respect cooldown
                if bars_since_last_exit >= self.strategy.config.cooldown_bars:
                    # Check risk constraints
                    trade_allowed, risk_reason = self.risk_manager.check_trade_allowed(current_equity=equity)
                    if trade_allowed:
                        signal = self.strategy.evaluate_bar(
                            bar_idx=i,
                            bar_data=bar.to_dict(),
                            current_spread_pips=spread
                        )

                        if signal.decision in {SignalDecision.BUY, SignalDecision.SELL}:
                            pending_order = {
                                "type": signal.decision.value,
                                "stop_distance_pips": signal.stop_distance_pips,
                                "target_distance_pips": signal.target_distance_pips,
                                "reason": signal.reason,
                                "signal_bar": i,
                                "signal_time": bar_time,
                            }

            # 6. Mark-to-market Equity Tracking
            floating_pnl = 0.0
            if open_position is not None:
                pos_type = open_position["type"]
                entry_p = open_position["entry_price"]
                vol = open_position["volume"]
                # Floating PnL evaluated at current bar close price
                pip_diff = (
                    (close_p - entry_p) / 0.0001
                    if pos_type == "BUY"
                    else (entry_p - close_p) / 0.0001
                )
                floating_pnl = pip_diff * 10.0 * vol

            current_equity = balance + floating_pnl
            equity = current_equity
            peak_equity = max(peak_equity, current_equity)
            drawdown_amt = peak_equity - current_equity
            drawdown_pct = (drawdown_amt / peak_equity * 100.0) if peak_equity > 0 else 0.0

            # Record sample point periodically (every 5 bars) and on last bar
            if i % 5 == 0 or i == end_i - 1:
                equity_curve.append({
                    "time": bar_time,
                    "bar_index": i,
                    "balance": round(balance, 2),
                    "equity": round(current_equity, 2),
                    "drawdown_pct": round(drawdown_pct, 2)
                })

        return {
            "initial_balance": self.initial_balance,
            "final_balance": round(balance, 2),
            "final_equity": round(equity, 2),
            "net_pnl": round(balance - self.initial_balance, 2),
            "trades": trades,
            "equity_curve": equity_curve,
            "cost_scenario": self.cost_model.config.to_dict(),
            "strategy_config": self.strategy.config.to_dict(),
            "risk_config": self.risk_manager.config.to_dict(),
        }
