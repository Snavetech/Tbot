"""
Market Data Service: Indicator calculations, volatility estimation,
support/resistance detection, and market regime classification.
"""
from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np


class MarketDataService:
    """Calculates quantitative features and classifies market regime"""

    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate EMAs, RSI, ATR, and Bollinger Bands on closed candles.
        Input dataframe must contain: time, open, high, low, close, volume.
        """
        if len(df) < 30:
            return df

        df = df.copy()

        # 1. Exponential Moving Averages
        df["ema_fast"] = df["close"].ewm(span=20, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=50, adjust=False).mean()
        df["ema_trend"] = df["close"].ewm(span=200, adjust=False).mean()

        # 2. RSI (Relative Strength Index, 14 periods)
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        df["rsi"] = 100 - (100 / (1 + rs))

        # 3. ATR (Average True Range, 14 periods)
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = tr.rolling(window=14).mean()

        # 4. Bollinger Bands (20 periods, 2 standard deviations)
        rolling_mean = df["close"].rolling(window=20).mean()
        rolling_std = df["close"].rolling(window=20).std()
        df["bb_middle"] = rolling_mean
        df["bb_upper"] = rolling_mean + (rolling_std * 2.0)
        df["bb_lower"] = rolling_mean - (rolling_std * 2.0)
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / (rolling_mean + 1e-10)

        # 5. Support & Resistance (Pivot highs and lows over last 20 bars)
        df["support"] = df["low"].rolling(window=20).min()
        df["resistance"] = df["high"].rolling(window=20).max()

        return df

    @staticmethod
    def classify_regime(df: pd.DataFrame) -> Tuple[str, Dict[str, Any]]:
        """
        Classifies market regime into:
        1. trending (strong directional EMA alignment and slope)
        2. ranging (flat EMAs, oscillating price within BB)
        3. high_volatility (expanding ATR and wide Bollinger Bands)
        4. uncertain (conflicting signals or insufficient data)
        """
        if len(df) < 50:
            return "uncertain", {"reason": "Insufficient candle data"}

        latest = df.iloc[-1]
        prev = df.iloc[-5]

        atr = latest.get("atr", 0.0010)
        avg_atr = df["atr"].tail(50).mean() if "atr" in df else 0.0010
        bb_width = latest.get("bb_width", 0.005)
        avg_bb_width = df["bb_width"].tail(50).mean() if "bb_width" in df else 0.005

        ema_fast = latest.get("ema_fast", latest["close"])
        ema_slow = latest.get("ema_slow", latest["close"])
        ema_trend = latest.get("ema_trend", latest["close"])

        # Check for High Volatility
        is_high_vol = (atr > avg_atr * 1.6) or (bb_width > avg_bb_width * 1.6)

        # Check for Strong Trend
        fast_slope = (latest["ema_fast"] - prev["ema_fast"]) / (prev["ema_fast"] + 1e-10)
        ema_spread = abs(ema_fast - ema_slow) / (latest["close"] + 1e-10)

        is_uptrend = (ema_fast > ema_slow > ema_trend) and (fast_slope > 0.0003)
        is_downtrend = (ema_fast < ema_slow < ema_trend) and (fast_slope < -0.0003)

        rsi = latest.get("rsi", 50.0)

        details = {
            "atr": round(float(atr), 5),
            "avg_atr": round(float(avg_atr), 5),
            "rsi": round(float(rsi), 2),
            "ema_fast": round(float(ema_fast), 5),
            "ema_slow": round(float(ema_slow), 5),
            "ema_trend": round(float(ema_trend), 5),
            "bb_width": round(float(bb_width), 5),
            "fast_slope": round(float(fast_slope), 6),
            "support": round(float(latest.get("support", latest["low"])), 5),
            "resistance": round(float(latest.get("resistance", latest["high"])), 5),
        }

        if is_high_vol:
            return "high_volatility", details
        elif is_uptrend or is_downtrend:
            details["trend_direction"] = "BULLISH" if is_uptrend else "BEARISH"
            return "trending", details
        elif bb_width < avg_bb_width * 1.1 and 40.0 <= rsi <= 60.0:
            return "ranging", details
        else:
            return "uncertain", details
