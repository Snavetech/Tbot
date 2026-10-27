"""
Range-Bound Mean Reversion Strategy Module
Evaluates support/resistance extremes, Bollinger Band rejections,
RSI exhaustion hooks, and disables when range boundaries break down.
"""
from typing import Optional
import pandas as pd
from backend.app.strategies.base import BaseStrategy, SignalResult, SignalType


class RangeBoundStrategy(BaseStrategy):
    """
    Evaluates mean reversion setups inside established trading ranges.
    Disables itself when range structure breaks down.
    """

    def __init__(self):
        super().__init__(name="range_bound", version="1.1.0")

    def evaluate(
        self,
        symbol: str,
        df_m15: pd.DataFrame,
        df_h1: Optional[pd.DataFrame] = None,
        current_spread_pips: float = 1.2
    ) -> SignalResult:
        if len(df_m15) < 30:
            return SignalResult(
                signal_type=SignalType.WAIT,
                symbol=symbol,
                strategy_name=self.name,
                entry_price=0.0,
                stop_loss=0.0,
                take_profit=0.0,
                reasoning_summary="Insufficient historical candles for range evaluation"
            )

        latest = df_m15.iloc[-1]
        prev = df_m15.iloc[-2]

        close_price = latest["close"]
        bb_upper = latest.get("bb_upper", close_price * 1.005)
        bb_middle = latest.get("bb_middle", close_price)
        bb_lower = latest.get("bb_lower", close_price * 0.995)
        bb_width = latest.get("bb_width", 0.005)
        rsi = latest.get("rsi", 50.0)
        atr = latest.get("atr", 0.0010)
        if atr <= 0:
            atr = 0.0010

        support = latest.get("support", close_price * 0.995)
        resistance = latest.get("resistance", close_price * 1.005)

        # Range Breakdown Condition: if BB width expands sharply or price breaks beyond support/resistance
        if bb_width > 0.0090:
            return SignalResult(
                signal_type=SignalType.WAIT,
                symbol=symbol,
                strategy_name=self.name,
                entry_price=round(close_price, 5),
                stop_loss=0.0,
                take_profit=0.0,
                market_regime="high_volatility",
                contradicting_evidence=["Bollinger Band expansion indicates volatile breakout"],
                reasoning_summary="Range strategy disabled due to high volatility expansion."
            )

        # 1. Range Support Bounce (BUY)
        # Price tested lower BB or support, closed back above, RSI oversold recovery
        is_range_buy = (
            (prev["low"] <= bb_lower or prev["low"] <= support)
            and latest["close"] > bb_lower
            and rsi <= 38.0
        )

        # 2. Range Resistance Rejection (SELL)
        # Price tested upper BB or resistance, closed back below, RSI overbought recovery
        is_range_sell = (
            (prev["high"] >= bb_upper or prev["high"] >= resistance)
            and latest["close"] < bb_upper
            and rsi >= 62.0
        )

        if is_range_buy:
            sl_distance = max(1.2 * atr, 0.0012)
            stop_loss = round(close_price - sl_distance, 5)
            take_profit = round(bb_middle, 5)
            reward = take_profit - close_price
            rr = round(reward / sl_distance, 2) if sl_distance > 0 else 1.5

            if rr >= 1.2:
                return SignalResult(
                    signal_type=SignalType.BUY,
                    symbol=symbol,
                    strategy_name=self.name,
                    entry_price=round(close_price, 5),
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    risk_reward_ratio=rr,
                    strategy_version=self.version,
                    market_regime="ranging",
                    supporting_evidence=[
                        f"Price rejected lower range band at {round(bb_lower, 5)}",
                        f"RSI oversold hook confirmed at {round(rsi, 1)}",
                        f"Targeting range midpoint at {round(bb_middle, 5)}",
                    ],
                    contradicting_evidence=[],
                    invalidation_conditions=[
                        f"Range breakdown below support at {stop_loss}",
                        "Surge in tick volume with downward breakout candle",
                    ],
                    reasoning_summary=f"Range support bounce setup on {symbol} with {rr} R:R."
                )

        if is_range_sell:
            sl_distance = max(1.2 * atr, 0.0012)
            stop_loss = round(close_price + sl_distance, 5)
            take_profit = round(bb_middle, 5)
            reward = close_price - take_profit
            rr = round(reward / sl_distance, 2) if sl_distance > 0 else 1.5

            if rr >= 1.2:
                return SignalResult(
                    signal_type=SignalType.SELL,
                    symbol=symbol,
                    strategy_name=self.name,
                    entry_price=round(close_price, 5),
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    risk_reward_ratio=rr,
                    strategy_version=self.version,
                    market_regime="ranging",
                    supporting_evidence=[
                        f"Price rejected upper range band at {round(bb_upper, 5)}",
                        f"RSI overbought hook confirmed at {round(rsi, 1)}",
                        f"Targeting range midpoint at {round(bb_middle, 5)}",
                    ],
                    contradicting_evidence=[],
                    invalidation_conditions=[
                        f"Range breakout above resistance at {stop_loss}",
                        "Surge in tick volume with upward breakout candle",
                    ],
                    reasoning_summary=f"Range resistance rejection setup on {symbol} with {rr} R:R."
                )

        return SignalResult(
            signal_type=SignalType.WAIT,
            symbol=symbol,
            strategy_name=self.name,
            entry_price=round(close_price, 5),
            stop_loss=0.0,
            take_profit=0.0,
            risk_reward_ratio=0.0,
            strategy_version=self.version,
            market_regime="ranging",
            supporting_evidence=[],
            contradicting_evidence=["Price in middle of range without boundary rejection"],
            invalidation_conditions=[],
            reasoning_summary="Price oscillating within range boundaries without confirmed setup."
        )
