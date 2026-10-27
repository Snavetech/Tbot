"""
Historical Data Ingestion & Quality Validation Module
Parses historical Forex candlestick CSVs, normalizes timestamps to UTC,
validates OHLC price relationships, and reports data quality diagnostics.
"""
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timezone
import io
import pandas as pd
import numpy as np


class DataQualityReport:
    """
    Structured diagnostic report for ingested candlestick data.
    """
    def __init__(
        self,
        source_name: str,
        total_rows: int,
        valid_rows: int,
        rejected_rows: int,
        duplicate_timestamps: int,
        cadence_seconds: Optional[int],
        detected_gaps: int,
        start_time_utc: Optional[str],
        end_time_utc: Optional[str],
        available_columns: List[str],
        has_historical_spread: bool,
        assumed_spread_pips: float,
        warnings: List[str],
        errors: List[str]
    ):
        self.source_name = source_name
        self.total_rows = total_rows
        self.valid_rows = valid_rows
        self.rejected_rows = rejected_rows
        self.duplicate_timestamps = duplicate_timestamps
        self.cadence_seconds = cadence_seconds
        self.detected_gaps = detected_gaps
        self.start_time_utc = start_time_utc
        self.end_time_utc = end_time_utc
        self.available_columns = available_columns
        self.has_historical_spread = has_historical_spread
        self.assumed_spread_pips = assumed_spread_pips
        self.warnings = warnings
        self.errors = errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "rejected_rows": self.rejected_rows,
            "duplicate_timestamps": self.duplicate_timestamps,
            "cadence_seconds": self.cadence_seconds,
            "detected_gaps": self.detected_gaps,
            "start_time_utc": self.start_time_utc,
            "end_time_utc": self.end_time_utc,
            "available_columns": self.available_columns,
            "has_historical_spread": self.has_historical_spread,
            "assumed_spread_pips": self.assumed_spread_pips,
            "warnings": self.warnings,
            "errors": self.errors,
            "is_valid": len(self.errors) == 0 and self.valid_rows > 0
        }


class HistoricalDataLoader:
    """
    Ingests and validates historical candlestick CSV datasets for EUR/USD research.
    """

    COLUMN_SYNONYMS = {
        "time": ["time", "datetime", "timestamp", "date", "gmt_time", "dtime"],
        "open": ["open", "o", "open_price"],
        "high": ["high", "h", "high_price"],
        "low": ["low", "l", "low_price"],
        "close": ["close", "c", "close_price"],
        "volume": ["tick_volume", "volume", "vol", "v", "ticks"],
        "spread": ["spread", "sprd", "spread_pips", "bid_ask_spread"]
    }

    @classmethod
    def load_from_csv(
        cls,
        file_source: Any,
        source_name: str = "custom_upload.csv",
        default_spread_pips: float = 1.2,
        expected_cadence_seconds: Optional[int] = 900  # Default 15m (900s)
    ) -> Tuple[Optional[pd.DataFrame], DataQualityReport]:
        """
        Load and validate historical candles from CSV path, file object, or string.
        Returns cleaned DataFrame and DataQualityReport.
        """
        warnings: List[str] = []
        errors: List[str] = []

        try:
            if isinstance(file_source, (str, Path)):
                df_raw = pd.read_csv(file_source)
            elif hasattr(file_source, "read"):
                # File-like object (e.g. UploadFile from FastAPI)
                content = file_source.read()
                if isinstance(content, bytes):
                    content = content.decode("utf-8", errors="replace")
                df_raw = pd.read_csv(io.StringIO(content))
            else:
                raise ValueError("Unsupported file source type")
        except Exception as e:
            return None, DataQualityReport(
                source_name=source_name,
                total_rows=0,
                valid_rows=0,
                rejected_rows=0,
                duplicate_timestamps=0,
                cadence_seconds=expected_cadence_seconds,
                detected_gaps=0,
                start_time_utc=None,
                end_time_utc=None,
                available_columns=[],
                has_historical_spread=False,
                assumed_spread_pips=default_spread_pips,
                warnings=[],
                errors=[f"Failed to read CSV: {str(e)}"]
            )

        total_rows = len(df_raw)
        if total_rows == 0:
            return None, DataQualityReport(
                source_name=source_name,
                total_rows=0,
                valid_rows=0,
                rejected_rows=0,
                duplicate_timestamps=0,
                cadence_seconds=expected_cadence_seconds,
                detected_gaps=0,
                start_time_utc=None,
                end_time_utc=None,
                available_columns=list(df_raw.columns),
                has_historical_spread=False,
                assumed_spread_pips=default_spread_pips,
                warnings=[],
                errors=["CSV file is empty."]
            )

        # 1. Map columns
        col_map = cls._map_columns(df_raw.columns)
        missing_core = [col for col in ["time", "open", "high", "low", "close"] if col not in col_map]
        if missing_core:
            return None, DataQualityReport(
                source_name=source_name,
                total_rows=total_rows,
                valid_rows=0,
                rejected_rows=total_rows,
                duplicate_timestamps=0,
                cadence_seconds=expected_cadence_seconds,
                detected_gaps=0,
                start_time_utc=None,
                end_time_utc=None,
                available_columns=list(df_raw.columns),
                has_historical_spread=False,
                assumed_spread_pips=default_spread_pips,
                warnings=[],
                errors=[f"Required core OHLC columns missing: {missing_core}"]
            )

        df = pd.DataFrame()
        # Rename mapped columns
        for canonical, orig in col_map.items():
            df[canonical] = df_raw[orig]

        # 2. Parse and normalize timestamp to UTC
        try:
            # Handle numeric timestamps (epoch seconds or ms) vs date strings
            sample_val = df["time"].iloc[0]
            if isinstance(sample_val, (int, float, np.integer, np.floating)):
                # If timestamp is in milliseconds (> 1e11), convert to seconds
                if sample_val > 1e11:
                    df["datetime"] = pd.to_datetime(df["time"] / 1000.0, unit="s", utc=True)
                else:
                    df["datetime"] = pd.to_datetime(df["time"], unit="s", utc=True)
            else:
                df["datetime"] = pd.to_datetime(df["time"], utc=True)
        except Exception as e:
            return None, DataQualityReport(
                source_name=source_name,
                total_rows=total_rows,
                valid_rows=0,
                rejected_rows=total_rows,
                duplicate_timestamps=0,
                cadence_seconds=expected_cadence_seconds,
                detected_gaps=0,
                start_time_utc=None,
                end_time_utc=None,
                available_columns=list(df_raw.columns),
                has_historical_spread=False,
                assumed_spread_pips=default_spread_pips,
                warnings=[],
                errors=[f"Timestamp parsing failed: {str(e)}"]
            )

        # Store standardized integer timestamp in seconds
        df["time"] = (df["datetime"] - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds().astype("int64")

        # 3. Sort chronologically
        is_sorted = df["time"].is_monotonic_increasing
        if not is_sorted:
            warnings.append("Dataset timestamps were not strictly sorted. Re-sorted chronologically.")
            df = df.sort_values("time").reset_index(drop=True)

        # 4. Check duplicate timestamps
        dup_count = int(df["time"].duplicated().sum())
        if dup_count > 0:
            warnings.append(f"Detected {dup_count} duplicate timestamps. Deduplicated keeping the first occurrence.")
            df = df.drop_duplicates(subset=["time"], keep="first").reset_index(drop=True)

        # 5. Validate OHLC price relationships
        price_cols = ["open", "high", "low", "close"]
        for p in price_cols:
            df[p] = pd.to_numeric(df[p], errors="coerce")

        initial_len = len(df)
        # Check non-null and positive
        valid_mask = (
            df["open"].notna() & (df["open"] > 0) &
            df["high"].notna() & (df["high"] > 0) &
            df["low"].notna() & (df["low"] > 0) &
            df["close"].notna() & (df["close"] > 0)
        )

        # Check OHLC logical constraints:
        # High must be >= max(open, close, low)
        # Low must be <= min(open, close, high)
        ohlc_valid_mask = (
            (df["high"] >= df["open"] - 1e-6) &
            (df["high"] >= df["close"] - 1e-6) &
            (df["high"] >= df["low"]) &
            (df["low"] <= df["open"] + 1e-6) &
            (df["low"] <= df["close"] + 1e-6)
        )

        combined_valid = valid_mask & ohlc_valid_mask
        invalid_rows_count = int((~combined_valid).sum())

        if invalid_rows_count > 0:
            warnings.append(f"Rejected {invalid_rows_count} rows with invalid OHLC relationships (e.g. High < Low or non-positive price).")
            df = df[combined_valid].reset_index(drop=True)

        if len(df) == 0:
            return None, DataQualityReport(
                source_name=source_name,
                total_rows=total_rows,
                valid_rows=0,
                rejected_rows=total_rows,
                duplicate_timestamps=dup_count,
                cadence_seconds=expected_cadence_seconds,
                detected_gaps=0,
                start_time_utc=None,
                end_time_utc=None,
                available_columns=list(df_raw.columns),
                has_historical_spread=False,
                assumed_spread_pips=default_spread_pips,
                warnings=warnings,
                errors=["No valid OHLC rows remaining after data quality validation."]
            )

        # 6. Check volume and spread columns
        if "volume" not in df.columns:
            df["volume"] = 1.0
            warnings.append("Volume column not found. Defaulting volume to 1.0.")
        else:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(1.0)

        has_spread = "spread" in df.columns
        if has_spread:
            df["spread"] = pd.to_numeric(df["spread"], errors="coerce")
            # If spread values are in broker raw points (> 5.0 for EURUSD), convert to pips
            if df["spread"].dropna().median() > 5.0:
                df["spread"] = df["spread"] / 10.0
            # Replace missing or non-positive spreads (e.g. unrecorded broker historical bars) with default
            zero_or_na = df["spread"].isna() | (df["spread"] <= 0)
            zero_count = int(zero_or_na.sum())
            if zero_count > 0:
                df.loc[zero_or_na, "spread"] = default_spread_pips
                warnings.append(f"Replaced {zero_count} unrecorded or zero spread candles with default assumption of {default_spread_pips:.1f} pips.")
        else:
            df["spread"] = default_spread_pips
            warnings.append(f"Historical spread column absent. Using documented default spread assumption of {default_spread_pips:.1f} pips.")

        # 7. Cadence and Gap Detection
        time_diffs = df["time"].diff().dropna()
        detected_cadence = int(time_diffs.median()) if len(time_diffs) > 0 else expected_cadence_seconds
        
        # Gap analysis: count intervals significantly larger than cadence (> 1.5x cadence)
        # Note: In Forex, weekends naturally have ~48h gaps (Friday 21:00 to Sunday 21:00 UTC)
        gaps_count = 0
        if detected_cadence and detected_cadence > 0:
            large_gaps = time_diffs[time_diffs > (detected_cadence * 1.5)]
            # Filter out standard weekend gaps (approx 45h to 55h = 162000 to 198000s)
            irregular_gaps = large_gaps[~large_gaps.between(150000, 205000)]
            gaps_count = len(irregular_gaps)
            if gaps_count > 0:
                warnings.append(f"Detected {gaps_count} missing candle gap(s) during weekday trading hours. Missing data reported without artificial interpolation.")

        start_time_utc = df["datetime"].iloc[0].strftime("%Y-%m-%d %H:%M:%S UTC")
        end_time_utc = df["datetime"].iloc[-1].strftime("%Y-%m-%d %H:%M:%S UTC")

        # Keep clean columns
        output_df = df[["time", "open", "high", "low", "close", "volume", "spread"]].copy()

        report = DataQualityReport(
            source_name=source_name,
            total_rows=total_rows,
            valid_rows=len(output_df),
            rejected_rows=total_rows - len(output_df),
            duplicate_timestamps=dup_count,
            cadence_seconds=detected_cadence,
            detected_gaps=gaps_count,
            start_time_utc=start_time_utc,
            end_time_utc=end_time_utc,
            available_columns=list(df_raw.columns),
            has_historical_spread=has_spread,
            assumed_spread_pips=default_spread_pips,
            warnings=warnings,
            errors=errors
        )

        return output_df, report

    @classmethod
    def _map_columns(cls, columns: List[str]) -> Dict[str, str]:
        """Maps arbitrary CSV header names to canonical names."""
        mapping = {}
        cols_lower = {c.strip().lower(): c for c in columns}

        for canonical, synonyms in cls.COLUMN_SYNONYMS.items():
            for syn in synonyms:
                if syn in cols_lower:
                    mapping[canonical] = cols_lower[syn]
                    break

        return mapping
