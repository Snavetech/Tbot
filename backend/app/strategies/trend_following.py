"""
Trend-Following Strategy Module
Evaluates higher-timeframe trend filter, moving average pullback,
RSI momentum confirmation, and ATR-based risk-reward exits.
"""
from typing import Optional
import pandas as pd
from backend.app.strategies.base import BaseStrategy, SignalResult, SignalType


class TrendFollowingStrategy(BaseStrategy):
    """
    Evaluates trending setups on M15 with H1 trend direction alignment.
    """

    def __init__(self):
        super().__init__(name="trend_following", version="1.1.0")

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
                reasoning_summary="Insufficient historical candles for M15 analysis"
            )

        latest = df_m15.iloc[-1]
        prev = df_m15.iloc[-2]

        close_price = latest["close"]
        ema_fast = latest.get("ema_fast", close_price)
        ema_slow = latest.get("ema_slow", close_price)
        rsi = latest.get("rsi", 50.0)
        atr = latest.get("atr", 0.0012)
        if atr <= 0:
            atr = 0.0012

        # 1. Higher-Timeframe Trend Confirmation (H1)
        htf_bullish = True
        htf_bearish = True
        if df_h1 is not None and len(df_h1) >= 20:
            h1_latest = df_h1.iloc[-1]
            h1_fast = h1_latest.get("ema_fast", h1_latest["close"])
            h1_slow = h1_latest.get("ema_slow", h1_latest["close"])
            htf_bullish = (h1_fast >= h1_slow)
            htf_bearish = (h1_fast <= h1_slow)

        # 2. Bullish Setup Criteria
        # - Fast EMA > Slow EMA
        # - H1 confirms bullish
        # - Price pulled back near EMA fast/slow and closed above EMA fast
        # - RSI between 50 and 68 (bullish momentum without extreme overbought)
        is_bullish_pullback = (
            ema_fast > ema_slow
            and htf_bullish
            and (prev["low"] <= ema_fast or prev["close"] <= ema_fast)
            and latest["close"] > ema_fast
            and 50.0 <= rsi <= 68.0
        )

        # 3. Bearish Setup Criteria
        # - Fast EMA < Slow EMA
        # - H1 confirms bearish
        # - Price pulled back near EMA fast/slow and closed below EMA fast
        # - RSI between 32 and 50 (bearish momentum without extreme oversold)
        is_bearish_pullback = (
            ema_fast < ema_slow
            and htf_bearish
            and (prev["high"] >= ema_fast or prev["close"] >= ema_fast)
            and latest["close"] < ema_fast
            and 32.0 <= rsi <= 50.0
        )

        if is_bullish_pullback:
            sl_distance = max(1.5 * atr, 0.0015)
            stop_loss = round(close_price - sl_distance, 5)
            take_profit = round(close_price + (sl_distance * 1.8), 5)

            return SignalResult(
                signal_type=SignalType.BUY,
                symbol=symbol,
                strategy_name=self.name,
                entry_price=round(close_price, 5),
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=1.8,
                strategy_version=self.version,
                market_regime="trending",
                supporting_evidence=[
                    f"M15 EMA fast ({round(ema_fast, 5)}) > EMA slow ({round(ema_slow, 5)})",
                    f"RSI bullish momentum confirmed at {round(rsi, 1)}",
                    "Price bounce confirmed above EMA fast after pullback",
                    "H1 higher-timeframe trend aligns bullish",
                ],
                contradicting_evidence=[],
                invalidation_conditions=[
                    f"Price drops below swing stop loss at {stop_loss}",
                    "RSI falls below 45 or EMAs bear-cross",
                ],
                reasoning_summary=f"Bullish trend pullback setup on {symbol} with 1.8 R:R target."
            )

        if is_bearish_pullback:
            sl_distance = max(1.5 * atr, 0.0015)
            stop_loss = round(close_price + sl_distance, 5)
            take_profit = round(close_price - (sl_distance * 1.8), 5)

            return SignalResult(
                signal_type=SignalType.SELL,
                symbol=symbol,
                strategy_name=self.name,
                entry_price=round(close_price, 5),
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=1.8,
                strategy_version=self.version,
                market_regime="trending",
                supporting_evidence=[
                    f"M15 EMA fast ({round(ema_fast, 5)}) < EMA slow ({round(ema_slow, 5)})",
                    f"RSI bearish momentum confirmed at {round(rsi, 1)}",
                    "Price rejection confirmed below EMA fast after pullback",
                    "H1 higher-timeframe trend aligns bearish",
                ],
                contradicting_evidence=[],
                invalidation_conditions=[
                    f"Price rallies above swing stop loss at {stop_loss}",
                    "RSI rises above 55 or EMAs bull-cross",
                ],
                reasoning_summary=f"Bearish trend pullback setup on {symbol} with 1.8 R:R target."
            )

        # Default: WAIT
        contradicting = []
        if not (htf_bullish or htf_bearish):
            contradicting.append("Higher-timeframe trend direction is neutral")
        if rsi > 68:
            contradicting.append(f"RSI overbought ({round(rsi, 1)})")
        elif rsi < 32:
            contradicting.append(f"RSI oversold ({round(rsi, 1)})")

        return SignalResult(
            signal_type=SignalType.WAIT,
            symbol=symbol,
            strategy_name=self.name,
            entry_price=round(close_price, 5),
            stop_loss=0.0,
            take_profit=0.0,
            risk_reward_ratio=0.0,
            strategy_version=self.version,
            market_regime="trending",
            supporting_evidence=[],
            contradicting_evidence=contradicting,
            invalidation_conditions=[],
            reasoning_summary="No valid pullback entry trigger confirmed on trend strategy."
        )
