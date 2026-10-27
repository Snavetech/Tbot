"""
Quantitative Feature Engineering Pipeline
Calculates technical indicators without future look-ahead bias:
- EMA 50 & EMA 200 (Exponential Moving Averages)
- RSI 14 (Wilder's Relative Strength Index)
- ATR 14 (Average True Range volatility)
- Rolling Volatility (20-period std dev of log returns)
- Trend Direction (EMA 50 vs EMA 200)
- Optional H1 higher-timeframe trend alignment (leakage-free resampled)
"""
from typing import Optional, Tuple
import pandas as pd
import numpy as np


class FeaturePipeline:
    """
    Computes technical indicators and market features strictly using past and current prices.
    Excludes or identifies warm-up rows to prevent invalid indicator usage.
    """

    DEFAULT_WARMUP_BARS = 200

    @classmethod
    def calculate_features(
        cls,
        df_candles: pd.DataFrame,
        fast_ema_period: int = 50,
        slow_ema_period: int = 200,
        rsi_period: int = 14,
        atr_period: int = 14,
        volatility_period: int = 20,
        include_h1_features: bool = False
    ) -> pd.DataFrame:
        """
        Calculates all baseline indicators.
        Returns a new DataFrame containing computed indicators alongside original columns.
        """
        df = df_candles.copy()

        # Ensure close, high, low are float
        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)

        # 1. Exponential Moving Averages (EMA 50 and EMA 200)
        # Mathematical Definition:
        # EMA_t = alpha * Close_t + (1 - alpha) * EMA_{t-1}, where alpha = 2 / (period + 1)
        # adjust=False enforces the recursive formulation matching financial terminal standards
        df["ema_50"] = close.ewm(span=fast_ema_period, adjust=False).mean()
        df["ema_200"] = close.ewm(span=slow_ema_period, adjust=False).mean()

        # 2. Relative Strength Index (RSI 14)
        # Mathematical Definition:
        # RS = AvgGain / AvgLoss using Wilder's exponential smoothing (alpha = 1 / period)
        # RSI = 100 - (100 / (1 + RS))
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(alpha=1.0 / rsi_period, min_periods=rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / rsi_period, min_periods=rsi_period, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        # Handle zero-loss edge case (RSI = 100) and zero-gain edge case (RSI = 50)
        zero_loss_mask = (avg_loss == 0)
        rsi = rsi.where(~(zero_loss_mask & (avg_gain > 0)), 100.0)
        rsi = rsi.where(~(zero_loss_mask & (avg_gain == 0)), 50.0)
        df["rsi_14"] = rsi

        # 3. Average True Range (ATR 14)
        # True Range: max(High - Low, |High - Close_{prev}|, |Low - Close_{prev}|)
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Wilder's smoothing for ATR (alpha = 1 / period)
        df["atr_14"] = tr.ewm(alpha=1.0 / atr_period, min_periods=atr_period, adjust=False).mean()

        # 4. Rolling Volatility (20-period standard deviation of log returns)
        # log_return_t = ln(close_t / close_{t-1})
        log_ret = np.log(close / prev_close)
        df["rolling_volatility_20"] = log_ret.rolling(window=volatility_period, min_periods=volatility_period).std()

        # 5. Trend Direction
        # UP: ema_50 > ema_200 (separation > 0.5 pip)
        # DOWN: ema_50 < ema_200 (separation > 0.5 pip)
        # FLAT: separation <= 0.5 pip
        ema_diff = df["ema_50"] - df["ema_200"]
        threshold = 0.00005  # 0.5 pip for EURUSD
        
        conditions = [
            ema_diff > threshold,
            ema_diff < -threshold
        ]
        choices = ["UP", "DOWN"]
        df["trend_direction"] = np.select(conditions, choices, default="FLAT")

        # 6. Optional Higher-Timeframe (H1) Trend Features
        if include_h1_features and "time" in df.columns and len(df) >= 300:
            df = cls._add_h1_features(df, fast_period=fast_ema_period, slow_period=slow_ema_period)
        else:
            df["h1_trend_direction"] = "UNKNOWN"
            df["h1_ema_50"] = np.nan
            df["h1_ema_200"] = np.nan

        # 7. Warm-up mask
        # Warmup period is defined by slow_ema_period (200 bars)
        df["is_warmup"] = df.index < max(slow_ema_period, 200)

        return df

    @classmethod
    def _add_h1_features(
        cls,
        df: pd.DataFrame,
        fast_period: int = 50,
        slow_period: int = 200
    ) -> pd.DataFrame:
        """
        Resamples M15 candles to H1, calculates H1 indicators, and maps back to M15
        using STRICT forward-shift to guarantee ZERO future leakage.
        """
        # Create datetime index for resampling
        temp = df.copy()
        temp["dt"] = pd.to_datetime(temp["time"], unit="s", utc=True)
        temp = temp.set_index("dt")

        # Resample to 1-Hour candles
        h1 = temp.resample("1h").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }).dropna()

        if len(h1) < slow_period:
            df["h1_trend_direction"] = "UNKNOWN"
            df["h1_ema_50"] = np.nan
            df["h1_ema_200"] = np.nan
            return df

        # Compute H1 indicators
        h1["h1_ema_50"] = h1["close"].ewm(span=fast_period, adjust=False).mean()
        h1["h1_ema_200"] = h1["close"].ewm(span=slow_period, adjust=False).mean()
        h1["h1_trend"] = np.where(h1["h1_ema_50"] > h1["h1_ema_200"], "UP", "DOWN")

        # CRITICAL LEAKAGE PREVENTION:
        # An H1 candle spanning 10:00 to 11:00 closes at 11:00.
        # Its features become available ONLY for M15 candles opening at 11:00 or later!
        # Therefore, shift H1 features forward by 1 hour (1 period)
        h1_shifted = h1[["h1_ema_50", "h1_ema_200", "h1_trend"]].shift(1)

        # Merge back onto M15 datetime index using merge_asof backward
        temp_reset = temp.reset_index()
        h1_reset = h1_shifted.reset_index().rename(columns={"dt": "h1_dt"})
        
        merged = pd.merge_asof(
            temp_reset.sort_values("dt"),
            h1_reset.sort_values("h1_dt"),
            left_on="dt",
            right_on="h1_dt",
            direction="backward"
        )

        df["h1_ema_50"] = merged["h1_ema_50"].values
        df["h1_ema_200"] = merged["h1_ema_200"].values
        df["h1_trend_direction"] = merged["h1_trend"].fillna("UNKNOWN").values

        return df
