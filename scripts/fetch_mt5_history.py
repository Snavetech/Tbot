#!/usr/bin/env python3
"""
TradePilot AI - Exness MT5 Historical Data Exporter
Retrieves the maximum available historical EUR/USD candlestick data
from a locally running MetaTrader 5 terminal without credentials,
validates data quality, and saves cleaned datasets to data/historical/.

STRICT READ-ONLY: Never places, modifies, or closes trades.
"""

import sys
import os
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

import pandas as pd
import numpy as np

# Safe import of official MetaTrader 5 package
try:
    import MetaTrader5 as mt5
except ImportError:
    print("[-] Error: 'MetaTrader5' Python package is not installed in the active environment.")
    print("    Install it via: pip install MetaTrader5 pandas numpy")
    sys.exit(1)


TIMEFRAME_MAP = {
    "M1": (mt5.TIMEFRAME_M1, 60),
    "M5": (mt5.TIMEFRAME_M5, 300),
    "M15": (mt5.TIMEFRAME_M15, 900),
    "M30": (mt5.TIMEFRAME_M30, 1800),
    "H1": (mt5.TIMEFRAME_H1, 3600),
    "H4": (mt5.TIMEFRAME_H4, 14400),
    "D1": (mt5.TIMEFRAME_D1, 86400),
}


def connect_terminal() -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Connects to the currently running MT5 terminal.
    Does not request or store any account passwords.
    """
    print("[*] Connecting to running MetaTrader 5 terminal...")
    if not mt5.initialize():
        err_code, err_msg = mt5.last_error()
        print(f"[-] mt5.initialize() failed. Error ({err_code}): {err_msg}")
        print("    Please ensure Exness MetaTrader 5 terminal is currently running on Windows and logged in.")
        return False, None

    term_info = mt5.terminal_info()
    acc_info = mt5.account_info()

    if term_info is None or not term_info.connected:
        print("[-] Warning: MT5 terminal reported not connected to broker trade server.")

    terminal_data = {
        "terminal_name": term_info.name if term_info else "Unknown",
        "terminal_company": term_info.company if term_info else "Unknown",
        "terminal_build": term_info.build if term_info else 0,
        "terminal_connected": term_info.connected if term_info else False,
        "account_login": acc_info.login if acc_info else None,
        "account_server": acc_info.server if acc_info else None,
        "account_company": acc_info.company if acc_info else None,
        "account_currency": acc_info.currency if acc_info else None,
        "trade_mode": acc_info.trade_mode if acc_info else None,
    }

    print(f"[+] Successfully connected to {terminal_data['terminal_name']} (Build {terminal_data['terminal_build']})")
    print(f"    Broker Server : {terminal_data['account_server']} ({terminal_data['account_company']})")
    print(f"    Account Login : {terminal_data['account_login']} [{terminal_data['account_currency']}]")
    print("    Safety Mode   : STRICT READ-ONLY (Zero trading/order execution capability)")

    return True, terminal_data


def detect_eurusd_symbol(symbol_override: Optional[str] = None) -> Optional[str]:
    """
    Detects the exact EUR/USD symbol available in the connected Exness terminal.
    Exness standard accounts typically use 'EURUSDm', while raw spread uses 'EURUSD', etc.
    """
    if symbol_override:
        info = mt5.symbol_info(symbol_override)
        if info is not None:
            mt5.symbol_select(symbol_override, True)
            print(f"[+] Using specified symbol: {symbol_override}")
            return symbol_override
        print(f"[-] Specified symbol '{symbol_override}' not found in terminal. Scanning available symbols...")

    all_symbols = mt5.symbols_get()
    if not all_symbols:
        print("[-] No symbols returned by mt5.symbols_get().")
        return None

    # Priority candidate check:
    # 1. Exact match 'EURUSD'
    # 2. Common Exness broker variants: 'EURUSDm', 'EURUSDc', 'EURUSD_i', 'EURUSD.'
    exact_match = None
    variant_matches = []

    for s in all_symbols:
        name_clean = s.name.strip()
        name_upper = name_clean.upper()

        if name_upper == "EURUSD":
            exact_match = name_clean
            break
        elif "EURUSD" in name_upper:
            variant_matches.append(name_clean)

    chosen_symbol = exact_match or (variant_matches[0] if variant_matches else None)

    if not chosen_symbol:
        print("[-] Could not find any EUR/USD symbol in terminal Market Watch.")
        return None

    # Ensure symbol is selected and visible
    mt5.symbol_select(chosen_symbol, True)
    sym_info = mt5.symbol_info(chosen_symbol)

    print(f"[+] Detected EUR/USD symbol: '{chosen_symbol}'")
    if sym_info:
        print(f"    Description  : {sym_info.description}")
        print(f"    Digits       : {sym_info.digits} (Point: {sym_info.point})")
        print(f"    Spread       : {sym_info.spread} points ({sym_info.spread / 10.0:.1f} pips)")
        print(f"    Contract Size: {sym_info.trade_contract_size:,.0f} {sym_info.currency_base}")

    return chosen_symbol


def fetch_all_candles(
    symbol: str,
    timeframe_str: str,
    batch_size: int = 25000
) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    """
    Paginates backward through MT5 candle history in batches of `batch_size`
    until the terminal's historical records are completely exhausted.
    """
    tf_tuple = TIMEFRAME_MAP.get(timeframe_str.upper())
    if not tf_tuple:
        raise ValueError(f"Unsupported timeframe: {timeframe_str}")

    tf_code, cadence_sec = tf_tuple
    offset = 0
    all_chunks: List[pd.DataFrame] = []
    mt5_errors: List[str] = []

    print(f"\n[*] Requesting maximum {timeframe_str} history for '{symbol}' in {batch_size:,}-bar batches...")

    while True:
        rates = mt5.copy_rates_from_pos(symbol, tf_code, offset, batch_size)

        if rates is None or len(rates) == 0:
            err_code, err_msg = mt5.last_error()
            if err_code != 1:  # 1 is Success / No error
                mt5_errors.append(f"Offset {offset}: Error ({err_code}): {err_msg}")
            print(f"    Reached earliest terminal history at offset {offset:,}. (Terminal history boundary)")
            break

        chunk_df = pd.DataFrame(rates)
        chunk_len = len(chunk_df)
        all_chunks.append(chunk_df)

        first_t = datetime.fromtimestamp(chunk_df["time"].iloc[0], timezone.utc).strftime("%Y-%m-%d %H:%M")
        last_t = datetime.fromtimestamp(chunk_df["time"].iloc[-1], timezone.utc).strftime("%Y-%m-%d %H:%M")

        print(f"    [Batch {len(all_chunks):02d}] Fetched {chunk_len:,} bars | Span: {first_t} to {last_t}")

        offset += chunk_len

        # If terminal returned fewer candles than requested, boundary was reached
        if chunk_len < batch_size:
            print(f"    Terminal returned {chunk_len:,} < {batch_size:,} bars. Historical limit reached.")
            break

    if not all_chunks:
        return None, {
            "total_fetched": 0,
            "mt5_errors": mt5_errors,
            "cadence_seconds": cadence_sec
        }

    raw_df = pd.concat(all_chunks, ignore_index=True)
    return raw_df, {
        "total_fetched": len(raw_df),
        "mt5_errors": mt5_errors,
        "cadence_seconds": cadence_sec
    }


def clean_and_validate_dataset(
    df_raw: pd.DataFrame,
    cadence_seconds: int,
    digits: int = 5
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Cleans raw MT5 candle dataframe:
    - Sorts chronologically
    - Deduplicates timestamps
    - Validates OHLC integrity
    - Formats UTC timestamps
    - Analyzes gaps (weekend vs weekday trading hours)
    """
    total_raw = len(df_raw)

    # 1. Sort chronologically
    df = df_raw.sort_values("time").reset_index(drop=True)

    # 2. Check and remove duplicate timestamps
    dup_mask = df["time"].duplicated()
    dup_count = int(dup_mask.sum())
    if dup_count > 0:
        df = df.drop_duplicates(subset=["time"], keep="first").reset_index(drop=True)

    # 3. Add human-readable UTC timestamp
    df["datetime_utc"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.strftime("%Y-%m-%d %H:%M:%S")

    # 4. Standardize numeric columns
    price_cols = ["open", "high", "low", "close"]
    for col in price_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").round(digits)

    if "tick_volume" in df.columns:
        df["tick_volume"] = pd.to_numeric(df["tick_volume"], errors="coerce").fillna(0).astype("int64")
    else:
        df["tick_volume"] = 1

    if "real_volume" in df.columns:
        df["real_volume"] = pd.to_numeric(df["real_volume"], errors="coerce").fillna(0).astype("int64")
    else:
        df["real_volume"] = 0

    if "spread" in df.columns:
        df["spread"] = pd.to_numeric(df["spread"], errors="coerce").fillna(0)
    else:
        df["spread"] = 0

    # 5. OHLC Price Integrity Constraints
    valid_mask = (
        (df["open"] > 0) &
        (df["high"] > 0) &
        (df["low"] > 0) &
        (df["close"] > 0) &
        (df["high"] >= df["open"] - 1e-6) &
        (df["high"] >= df["close"] - 1e-6) &
        (df["high"] >= df["low"]) &
        (df["low"] <= df["open"] + 1e-6) &
        (df["low"] <= df["close"] + 1e-6)
    )

    invalid_count = int((~valid_mask).sum())
    if invalid_count > 0:
        df = df[valid_mask].reset_index(drop=True)

    # 6. Gap Diagnostics
    time_diffs = df["time"].diff().dropna()
    irregular_gaps = []
    weekend_closures = 0
    weekday_gaps = 0

    if len(time_diffs) > 0:
        gaps_mask = time_diffs > (cadence_seconds * 1.5)
        gap_indices = time_diffs[gaps_mask].index

        for idx in gap_indices:
            gap_duration = int(time_diffs.loc[idx])
            t_start = datetime.fromtimestamp(df.loc[idx - 1, "time"], timezone.utc)
            t_end = datetime.fromtimestamp(df.loc[idx, "time"], timezone.utc)

            # Normal Forex weekend closure: Friday ~21:00 UTC to Sunday ~21:00 UTC (~150,000s to 205,000s)
            if 150000 <= gap_duration <= 205000:
                weekend_closures += 1
            else:
                weekday_gaps += 1
                irregular_gaps.append({
                    "start": t_start.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "end": t_end.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "duration_hours": round(gap_duration / 3600.0, 1),
                })

    earliest_dt = datetime.fromtimestamp(df["time"].iloc[0], timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    latest_dt = datetime.fromtimestamp(df["time"].iloc[-1], timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Order columns canonically for TradePilot AI ingestion
    canonical_columns = [
        "time",
        "datetime_utc",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
        "spread",
        "real_volume"
    ]
    cleaned_df = df[canonical_columns].copy()

    diagnostics = {
        "total_raw": total_raw,
        "valid_candles": len(cleaned_df),
        "duplicate_timestamps_removed": dup_count,
        "invalid_ohlc_rejected": invalid_count,
        "weekend_closures": weekend_closures,
        "weekday_gaps": weekday_gaps,
        "irregular_gaps_details": irregular_gaps[:5],  # top 5
        "earliest_timestamp": earliest_dt,
        "latest_timestamp": latest_dt,
    }

    return cleaned_df, diagnostics


def save_dataset_safely(
    df: pd.DataFrame,
    target_path: Path,
    overwrite: bool = False
) -> Path:
    """
    Saves dataframe to CSV ensuring existing datasets are never overwritten
    without explicit confirmation.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists() and not overwrite:
        # Check if stdin is an interactive terminal
        if sys.stdin.isatty():
            choice = input(f"[?] File '{target_path}' already exists. Overwrite? [y/N]: ").strip().lower()
            if choice not in ("y", "yes"):
                timestamp_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_path = target_path.with_name(f"{target_path.stem}_{timestamp_suffix}.csv")
                print(f"[*] Non-destructive write: Saving to new file '{target_path}'")
        else:
            # Non-interactive mode fallback to timestamped file to preserve existing data
            timestamp_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_path = target_path.with_name(f"{target_path.stem}_{timestamp_suffix}.csv")
            print(f"[*] Confirmation required: Preserving existing file. Saving to '{target_path}'")

    df.to_csv(target_path, index=False)
    file_size_mb = target_path.stat().st_size / (1024.0 * 1024.0)
    print(f"[+] Saved {len(df):,} rows to: {target_path} ({file_size_mb:.2f} MB)")
    return target_path


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve maximum available historical EUR/USD data from running Exness MT5 terminal."
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help="Specify symbol override (e.g. 'EURUSD' or 'EURUSDm'). Default: Auto-detect."
    )
    parser.add_argument(
        "--timeframes",
        nargs="+",
        default=["M15", "H1"],
        choices=list(TIMEFRAME_MAP.keys()),
        help="Timeframe(s) to retrieve. Default: M15 H1"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/historical",
        help="Target folder for historical CSV exports. Default: data/historical"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=25000,
        help="Batch size in bars per MT5 request. Default: 25000"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing CSV files without interactive confirmation."
    )

    args = parser.parse_args()

    print("=" * 75)
    print("  TradePilot AI - Exness MT5 Historical Data Extraction Utility")
    print("=" * 75)

    # 1. Connect to running terminal
    connected, term_info = connect_terminal()
    if not connected:
        sys.exit(1)

    try:
        # 2. Detect exact EURUSD symbol
        symbol = detect_eurusd_symbol(args.symbol)
        if not symbol:
            print("[-] Unable to proceed without a valid symbol. Exiting.")
            sys.exit(1)

        sym_digits = mt5.symbol_info(symbol).digits if mt5.symbol_info(symbol) else 5
        output_dir = Path(args.output_dir)

        # 3. Retrieve and process each requested timeframe
        results_summary = []

        for tf_str in args.timeframes:
            df_raw, fetch_meta = fetch_all_candles(symbol, tf_str, batch_size=args.batch_size)

            if df_raw is None or len(df_raw) == 0:
                print(f"[-] No historical data returned for {tf_str}.")
                results_summary.append({
                    "timeframe": tf_str,
                    "candles": 0,
                    "status": "FAILED",
                    "errors": fetch_meta.get("mt5_errors", [])
                })
                continue

            cleaned_df, diag = clean_and_validate_dataset(
                df_raw,
                cadence_seconds=fetch_meta["cadence_seconds"],
                digits=sym_digits
            )

            # Target filename: canonical format e.g. EURUSD_M15.csv
            target_csv = output_dir / f"EURUSD_{tf_str}.csv"
            saved_path = save_dataset_safely(cleaned_df, target_csv, overwrite=args.overwrite)

            results_summary.append({
                "timeframe": tf_str,
                "candles": diag["valid_candles"],
                "earliest": diag["earliest_timestamp"],
                "latest": diag["latest_timestamp"],
                "duplicates_removed": diag["duplicate_timestamps_removed"],
                "rejected_candles": diag["invalid_ohlc_rejected"],
                "weekend_closures": diag["weekend_closures"],
                "weekday_gaps": diag["weekday_gaps"],
                "irregular_gaps_details": diag["irregular_gaps_details"],
                "file_path": str(saved_path),
                "file_size_mb": round(saved_path.stat().st_size / (1024.0 * 1024.0), 2),
                "errors": fetch_meta.get("mt5_errors", []),
                "status": "SUCCESS"
            })

        # 4. Print honest diagnostic summary
        print("\n" + "=" * 75)
        print("  HISTORICAL DATA EXTRACTION AUDIT SUMMARY")
        print("=" * 75)

        for res in results_summary:
            print(f"\nTimeframe: {res['timeframe']}")
            if res["status"] == "SUCCESS":
                print(f"  Status             : SUCCESS")
                print(f"  Saved File         : {res['file_path']} ({res['file_size_mb']} MB)")
                print(f"  Total Valid Candles: {res['candles']:,}")
                print(f"  Earliest Candle    : {res['earliest']}")
                print(f"  Latest Candle      : {res['latest']}")
                print(f"  Duplicate Dropped  : {res['duplicates_removed']}")
                print(f"  Invalid OHLC Drops : {res['rejected_candles']}")
                print(f"  Weekend Closures   : {res['weekend_closures']} normal ~48h closures")
                print(f"  Weekday Gaps       : {res['weekday_gaps']} irregular gaps")
                if res["weekday_gaps"] > 0:
                    for g in res["irregular_gaps_details"]:
                        print(f"    * Gap: {g['duration_hours']}h from {g['start']} to {g['end']}")
                if res["errors"]:
                    print(f"  Terminal Logs      : {res['errors']}")
            else:
                print(f"  Status             : FAILED")
                print(f"  Errors             : {res['errors']}")

        print("\n[+] Verification Note:")
        print("    Data bounds represent the genuine historical limits provided by your broker's terminal.")
        print("    No artificial interpolation or synthetic candles were inserted.")
        print("=" * 75)

    finally:
        mt5.shutdown()
        print("[*] MT5 connection closed cleanly.")


if __name__ == "__main__":
    main()
