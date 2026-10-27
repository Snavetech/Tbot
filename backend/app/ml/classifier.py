"""
Machine Learning Classifier & Probability Calibrator
Trained with chronological time-series splitting to strictly avoid data leakage.
"""
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, brier_score_loss

from backend.app.ml.features import FeaturePipeline, FEATURE_COLUMNS
from backend.app.core.events import logger


class MLCalibrator:
    """
    Lightweight, locally-trained ML model providing calibrated direction probabilities.
    Always uses chronological train/test splitting.
    """

    MODEL_VERSION = "tradepilot-hgb-v1.0"

    def __init__(self):
        self.model: Optional[HistGradientBoostingClassifier] = None
        self.is_trained: bool = False
        self.metrics: Dict[str, float] = {}
        self.feature_names = FEATURE_COLUMNS

    def train_chronological(self, df_candles: pd.DataFrame, test_ratio: float = 0.25) -> Dict[str, Any]:
        """
        Train HistGradientBoostingClassifier using strict chronological split.
        """
        X_df, y_series = FeaturePipeline.extract_features(df_candles)

        n_samples = len(X_df)
        if n_samples < 60:
            return {"error": f"Insufficient data for training ({n_samples} samples, need >= 60)"}

        # Chronological index split
        split_idx = int(n_samples * (1.0 - test_ratio))
        X_train, X_test = X_df.iloc[:split_idx].values, X_df.iloc[split_idx:].values
        y_train, y_test = y_series.iloc[:split_idx].values, y_series.iloc[split_idx:].values

        model = HistGradientBoostingClassifier(
            max_iter=50,
            learning_rate=0.05,
            max_leaf_nodes=15,
            random_state=42
        )
        model.fit(X_train, y_train)

        # Evaluate on untouched chronological test set
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1] if len(model.classes_) > 1 else np.zeros_like(y_pred)

        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, zero_division=0))
        rec = float(recall_score(y_test, y_pred, zero_division=0))
        brier = float(brier_score_loss(y_test, y_prob))

        self.model = model
        self.is_trained = True
        self.metrics = {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "brier_score": round(brier, 4),
            "test_samples": len(y_test),
            "train_samples": len(y_train),
            "model_version": self.MODEL_VERSION
        }

        logger.info(f"Trained ML Calibrator {self.MODEL_VERSION}: Accuracy={acc:.3f}, Precision={prec:.3f}")
        return self.metrics

    def predict_confidence(self, df_candles: pd.DataFrame) -> Tuple[Optional[float], Optional[float]]:
        """
        Predict calibrated probability for latest feature state.
        Returns: (bullish_confidence, estimated_expectancy)
        """
        if not self.is_trained or self.model is None:
            # Self-train on historical data if not yet trained
            if len(df_candles) >= 80:
                self.train_chronological(df_candles)
            else:
                return None, None

        feat = FeaturePipeline.extract_inference_features(df_candles)
        try:
            probs = self.model.predict_proba(feat)[0]
            confidence = float(probs[1]) if len(probs) > 1 else 0.50
            # Expectancy estimate based on calibrated win rate and 1:1.5 payoff
            expectancy = round((confidence * 1.5) - ((1.0 - confidence) * 1.0), 3)
            return round(confidence, 3), expectancy
        except Exception as e:
            logger.warning(f"ML inference error: {e}")
            return None, None


# Global singleton instance of MLCalibrator
ml_calibrator = MLCalibrator()
