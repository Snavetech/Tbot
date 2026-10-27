"""
Quantitative feature engineering pipeline for machine learning models
"""
import numpy as np
import pandas as pd
from typing import Tuple, List


FEATURE_COLUMNS = [
    "returns_1",
    "returns_5",
    "rsi_norm",
    "atr_norm",
    "ema_fast_slope",
    "bb_pos",
    "vol_ratio"
]


class FeaturePipeline:
    """Extracts normalized chronological features without look-ahead bias"""

    @staticmethod
    def extract_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Extract features and future 3-bar target direction for training.
        Features use strictly backward-looking information.
        """
        df = df.copy()

        # Backward returns
        df["returns_1"] = df["close"].pct_change(1)
        df["returns_5"] = df["close"].pct_change(5)

        # Normalized RSI (0.0 to 1.0)
        df["rsi_norm"] = (df.get("rsi", pd.Series(50, index=df.index)) - 50.0) / 50.0

        # Normalized ATR
        atr = df.get("atr", pd.Series(0.001, index=df.index))
        df["atr_norm"] = (atr / (df["close"] + 1e-10)) * 100.0

        # EMA slope
        ema_fast = df.get("ema_fast", df["close"])
        df["ema_fast_slope"] = ema_fast.pct_change(3)

        # Position within Bollinger Bands (0.0 = lower band, 1.0 = upper band)
        bb_upper = df.get("bb_upper", df["close"] * 1.005)
        bb_lower = df.get("bb_lower", df["close"] * 0.995)
        bb_denom = (bb_upper - bb_lower).replace(0, np.nan)
        df["bb_pos"] = (df["close"] - bb_lower) / bb_denom
        df["bb_pos"] = df["bb_pos"].clip(-0.5, 1.5).fillna(0.5)

        # Volume ratio against rolling 20-period median
        vol = df.get("volume", pd.Series(100, index=df.index))
        vol_med = vol.rolling(20).median().replace(0, 100)
        df["vol_ratio"] = (vol / vol_med).clip(0.1, 5.0)

        # Target: Forward 3-bar return direction (1 = Bullish, 0 = Neutral/Bearish)
        # Note: ONLY used for offline model training/evaluation, never used at inference time!
        forward_returns = df["close"].shift(-3) - df["close"]
        target = (forward_returns > (atr * 0.5)).astype(int)

        # Drop initial NaN rows
        valid_idx = df[FEATURE_COLUMNS].dropna().index
        features_df = df.loc[valid_idx, FEATURE_COLUMNS]
        target_series = target.loc[valid_idx]

        return features_df, target_series

    @staticmethod
    def extract_inference_features(df: pd.DataFrame) -> np.ndarray:
        """Extract latest feature vector for real-time model inference"""
        features_df, _ = FeaturePipeline.extract_features(df)
        if len(features_df) == 0:
            return np.zeros((1, len(FEATURE_COLUMNS)))
        return features_df.iloc[-1:].values
