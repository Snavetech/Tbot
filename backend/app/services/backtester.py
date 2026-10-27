"""
Chronological Event-Driven Backtesting Engine
Simulates historical trades without broker orders, enforcing zero look-ahead bias,
realistic spread, commission, and conservative stop-loss / take-profit fills.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from backend.app.services.market_data import MarketDataService
from backend.app.strategies.trend_following import TrendFollowingStrategy
from backend.app.strategies.range_bound import RangeBoundStrategy
from backend.app.strategies.base import SignalType


class BacktestEngine:
    """
    Event-driven backtesting engine running bar-by-bar chronological evaluation.
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        spread_pips: float = 1.2,
        slippage_points: int = 5,
        commission_per_lot: float = 7.0,
        risk_per_trade_pct: float = 0.25
    ):
        self.initial_balance = initial_balance
        self.spread_pips = spread_pips
        self.spread_price = spread_pips * 0.0001
        self.slippage = (slippage_points * 0.1) * 0.0001
        self.commission_per_lot = commission_per_lot
        self.risk_per_trade_pct = risk_per_trade_pct

        self.trend_strat = TrendFollowingStrategy()
        self.range_strat = RangeBoundStrategy()

    def run_backtest(
        self,
        df_candles: pd.DataFrame,
        strategy_mode: str = "all",
        symbol: str = "EURUSD"
    ) -> Dict[str, Any]:
        """
        Execute chronological backtest over supplied candlestick dataframe.
        """
        if len(df_candles) < 60:
            return {"error": "Candle count too low for backtest (minimum 60 bars required)"}

        # Precalculate indicators
        df = MarketDataService.calculate_indicators(df_candles)

        balance = self.initial_balance
        equity = self.initial_balance
        peak_equity = self.initial_balance

        open_position: Optional[Dict[str, Any]] = None
        trades: List[Dict[str, Any]] = []
        equity_curve: List[Dict[str, Any]] = []

        # Chronological loop starting after indicator warm-up period (bar 35)
        for i in range(35, len(df)):
            current_bar = df.iloc[i]
            prev_bar = df.iloc[i - 1]
            sub_df = df.iloc[:i]  # Slice strictly up to previous closed bar!

            high_p = current_bar["high"]
            low_p = current_bar["low"]
            open_p = current_bar["open"]
            close_p = current_bar["close"]
            bar_time = int(current_bar["time"])

            # 1. Manage Active Position (Check Stop Loss and Take Profit on current bar's High/Low)
            if open_position is not None:
                pos_type = open_position["type"]
                entry_p = open_position["entry_price"]
                sl = open_position["sl"]
                tp = open_position["tp"]
                vol = open_position["volume"]

                exit_price = None
                exit_reason = None

                if pos_type == "BUY":
                    # Check SL first conservatively (worst case fill)
                    if low_p <= sl:
                        exit_price = sl - self.slippage
                        exit_reason = "STOP_LOSS"
                    elif high_p >= tp:
                        exit_price = tp
                        exit_reason = "TAKE_PROFIT"
                else:  # SELL
                    if high_p >= sl:
                        exit_price = sl + self.slippage
                        exit_reason = "STOP_LOSS"
                    elif low_p <= tp:
                        exit_price = tp
                        exit_reason = "TAKE_PROFIT"

                if exit_price is not None:
                    # Calculate PnL
                    pip_diff = (exit_price - entry_p) / 0.0001 if pos_type == "BUY" else (entry_p - exit_price) / 0.0001
                    gross_pnl = round(pip_diff * 10.0 * vol, 2)
                    comm = round(self.commission_per_lot * vol, 2)
                    net_pnl = round(gross_pnl - comm, 2)

                    balance += net_pnl
                    equity = balance

                    trade_record = {
                        "trade_num": len(trades) + 1,
                        "type": pos_type,
                        "volume": vol,
                        "entry_time": open_position["entry_time"],
                        "exit_time": bar_time,
                        "entry_price": entry_p,
                        "exit_price": round(exit_price, 5),
                        "sl": sl,
                        "tp": tp,
                        "gross_pnl": gross_pnl,
                        "commission": comm,
                        "net_pnl": net_pnl,
                        "exit_reason": exit_reason,
                        "strategy": open_position["strategy"],
                        "regime": open_position["regime"],
                    }
                    trades.append(trade_record)
                    open_position = None

            # 2. Evaluate Entry Setup if no open position
            if open_position is None:
                regime, _ = MarketDataService.classify_regime(sub_df)

                signal = None
                if strategy_mode in {"trend_following", "all"} and regime == "trending":
                    signal = self.trend_strat.evaluate(symbol, sub_df, current_spread_pips=self.spread_pips)
                elif strategy_mode in {"range_bound", "all"} and regime == "ranging":
                    signal = self.range_strat.evaluate(symbol, sub_df, current_spread_pips=self.spread_pips)

                if signal and signal.signal_type in {SignalType.BUY, SignalType.SELL}:
                    sig_type_str = signal.signal_type.value
                    # Execute on current bar's open price with spread
                    entry_exec = (open_p + self.spread_price) if sig_type_str == "BUY" else open_p

                    sl = signal.stop_loss
                    tp = signal.take_profit
                    sl_dist = abs(entry_exec - sl)

                    if sl_dist > 0.0002:
                        risk_dollars = equity * (self.risk_per_trade_pct / 100.0)
                        ticks = sl_dist / 0.00001
                        raw_vol = risk_dollars / (ticks * 1.0)
                        vol = max(0.01, min(10.0, round(raw_vol, 2)))

                        open_position = {
                            "type": sig_type_str,
                            "volume": vol,
                            "entry_price": round(entry_exec, 5),
                            "sl": sl,
                            "tp": tp,
                            "entry_time": bar_time,
                            "strategy": signal.strategy_name,
                            "regime": regime,
                        }

            # 3. Track Equity Curve and Drawdown
            floating_pnl = 0.0
            if open_position is not None:
                pos_type = open_position["type"]
                entry_p = open_position["entry_price"]
                vol = open_position["volume"]
                pip_diff = (close_p - entry_p) / 0.0001 if pos_type == "BUY" else (entry_p - close_p) / 0.0001
                floating_pnl = pip_diff * 10.0 * vol

            current_equity = balance + floating_pnl
            peak_equity = max(peak_equity, current_equity)
            drawdown_amt = peak_equity - current_equity
            drawdown_pct = (drawdown_amt / peak_equity * 100.0) if peak_equity > 0 else 0.0

            # Record sample point every 5 bars to keep payload concise
            if i % 5 == 0 or i == len(df) - 1:
                equity_curve.append({
                    "time": bar_time,
                    "balance": round(balance, 2),
                    "equity": round(current_equity, 2),
                    "drawdown_pct": round(drawdown_pct, 2)
                })

        # Calculate Summary Metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t["net_pnl"] > 0]
        losing_trades = [t for t in trades if t["net_pnl"] < 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = round((win_count / total_trades * 100.0), 2) if total_trades > 0 else 0.0

        gross_profit = sum(t["net_pnl"] for t in winning_trades)
        gross_loss = abs(sum(t["net_pnl"] for t in losing_trades))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

        total_net_pnl = round(balance - self.initial_balance, 2)
        avg_win = round(gross_profit / win_count, 2) if win_count > 0 else 0.0
        avg_loss = round(gross_loss / loss_count, 2) if loss_count > 0 else 0.0
        expectancy = round(((win_rate / 100.0) * avg_win) - (((100.0 - win_rate) / 100.0) * avg_loss), 2)

        max_dd_pct = max([p["drawdown_pct"] for p in equity_curve]) if equity_curve else 0.0

        return {
            "symbol": symbol,
            "strategy_mode": strategy_mode,
            "initial_balance": self.initial_balance,
            "final_balance": round(balance, 2),
            "net_pnl": total_net_pnl,
            "return_pct": round((total_net_pnl / self.initial_balance) * 100.0, 2),
            "metrics": {
                "total_trades": total_trades,
                "winning_trades": win_count,
                "losing_trades": loss_count,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "gross_profit": round(gross_profit, 2),
                "gross_loss": round(gross_loss, 2),
                "average_win": avg_win,
                "average_loss": avg_loss,
                "trade_expectancy": expectancy,
                "max_drawdown_pct": round(max_dd_pct, 2),
            },
            "equity_curve": equity_curve,
            "trades": trades,
            "data_limitations": [
                "Simulated historical M15 candle model; intra-bar ticks approximated by High/Low.",
                f"Modeled {self.spread_pips} pips fixed spread, {self.slippage * 10000:.1f} pips slippage.",
                "Historical backtest results are not guarantees of future performance."
            ]
        }
