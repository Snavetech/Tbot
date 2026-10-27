"""
Offline Research & Backtesting Engine Endpoints
Provides CSV uploading, data quality validation, chronological simulation,
parameter sensitivity grids, and PDF/CSV report downloads.
"""
from typing import Optional, Dict, Any
from pathlib import Path
import os
import io
import json
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.app.schemas.reports import BacktestRequest
from backend.app.services.backtester import BacktestEngine
from backend.app.services.mt5_adapter import mt5_adapter
from backend.app.backtesting import (
    HistoricalDataLoader,
    FeaturePipeline,
    StrategyConfig,
    CostModelConfig,
    CostModelPresets,
    RiskConfig,
    OfflineBacktestEngine,
    ChronologicalSplitter,
    PerformanceMetricsCalculator,
    BacktestReportGenerator,
)

router = APIRouter(prefix="/backtest", tags=["Backtesting"])

# In-memory session store for uploaded datasets and recent backtest runs
BACKTEST_CACHE_DIR = Path("data/backtest_cache")
BACKTEST_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_DATASET_CACHE: Dict[str, Any] = {}
_RESULTS_CACHE: Dict[str, Any] = {}


class OfflineRunRequest(BaseModel):
    dataset_id: Optional[str] = None
    initial_balance: float = Field(default=10000.0, ge=100.0)
    cost_scenario: str = Field(default="Normal")  # Normal, Elevated, Stressed
    fast_ema_period: int = Field(default=50, ge=5, le=200)
    slow_ema_period: int = Field(default=200, ge=20, le=500)
    rsi_period: int = Field(default=14, ge=2, le=50)
    rsi_long_min: float = Field(default=52.0, ge=10.0, le=90.0)
    rsi_long_max: float = Field(default=68.0, ge=10.0, le=90.0)
    rsi_short_min: float = Field(default=32.0, ge=10.0, le=90.0)
    rsi_short_max: float = Field(default=48.0, ge=10.0, le=90.0)
    atr_stop_multiplier: float = Field(default=1.5, ge=0.5, le=5.0)
    risk_reward_ratio: float = Field(default=2.0, ge=0.5, le=10.0)
    cooldown_bars: int = Field(default=2, ge=0, le=50)
    risk_per_trade_pct: float = Field(default=0.25, ge=0.01, le=5.0)
    max_daily_loss_pct: float = Field(default=1.0, ge=0.1, le=20.0)
    max_weekly_loss_pct: float = Field(default=3.0, ge=0.1, le=50.0)
    max_trades_per_day: int = Field(default=5, ge=1, le=50)
    run_partitioned_split: bool = Field(default=True)


@router.post("/upload-csv")
async def upload_csv_dataset(file: UploadFile = File(...)):
    """
    Ingests and validates historical EUR/USD CSV dataset.
    Returns data quality diagnostics and a session dataset_id.
    """
    dataset_id = str(uuid.uuid4())
    content = await file.read()

    df_cleaned, quality_report = HistoricalDataLoader.load_from_csv(
        file_source=io.BytesIO(content),
        source_name=file.filename or "uploaded.csv"
    )

    if df_cleaned is None or not quality_report.to_dict()["is_valid"]:
        return {
            "success": False,
            "dataset_id": None,
            "quality_report": quality_report.to_dict(),
            "preview": []
        }

    # Precalculate features on cleaned dataset
    df_features = FeaturePipeline.calculate_features(df_cleaned)

    # Cache dataset in memory
    _DATASET_CACHE[dataset_id] = {
        "df": df_features,
        "quality_report": quality_report.to_dict(),
        "filename": file.filename
    }

    # Generate preview (first 5 rows)
    preview_rows = df_cleaned.head(5).to_dict(orient="records")

    return {
        "success": True,
        "dataset_id": dataset_id,
        "quality_report": quality_report.to_dict(),
        "preview": preview_rows
    }


@router.post("/run-offline")
def run_offline_backtest(req: OfflineRunRequest):
    """
    Executes chronological event-driven backtest over uploaded CSV or synthetic baseline dataset.
    Supports Normal, Elevated, and Stressed cost scenarios and 60/20/20 train/val/test splits.
    """
    # 1. Retrieve dataset
    if req.dataset_id and req.dataset_id in _DATASET_CACHE:
        dataset_entry = _DATASET_CACHE[req.dataset_id]
        df_features = dataset_entry["df"]
        quality_report = dataset_entry["quality_report"]
    else:
        # Fallback to realistic synthetic or MT5 candle dataset if no CSV uploaded
        df_candles = mt5_adapter.get_candles(symbol="EURUSD", timeframe="M15", count=800)
        df_features = FeaturePipeline.calculate_features(df_candles)
        quality_report = {
            "source_name": "MT5 / In-Memory Baseline EURUSD (M15)",
            "total_rows": len(df_candles),
            "valid_rows": len(df_candles),
            "rejected_rows": 0,
            "duplicate_timestamps": 0,
            "cadence_seconds": 900,
            "detected_gaps": 0,
            "start_time_utc": None,
            "end_time_utc": None,
            "has_historical_spread": True,
            "assumed_spread_pips": 1.2,
            "warnings": ["Using baseline EUR/USD historical candle series."],
            "errors": []
        }

    # 2. Configure Cost Model
    if req.cost_scenario == "Elevated":
        cost_cfg = CostModelPresets.elevated()
    elif req.cost_scenario == "Stressed":
        cost_cfg = CostModelPresets.stressed()
    else:
        cost_cfg = CostModelPresets.normal()

    # 3. Configure Strategy & Risk
    strat_cfg = StrategyConfig(
        fast_ema_period=req.fast_ema_period,
        slow_ema_period=req.slow_ema_period,
        rsi_period=req.rsi_period,
        rsi_long_min=req.rsi_long_min,
        rsi_long_max=req.rsi_long_max,
        rsi_short_min=req.rsi_short_min,
        rsi_short_max=req.rsi_short_max,
        atr_stop_multiplier=req.atr_stop_multiplier,
        risk_reward_ratio=req.risk_reward_ratio,
        cooldown_bars=req.cooldown_bars,
    )

    risk_cfg = RiskConfig(
        risk_per_trade_pct=req.risk_per_trade_pct,
        max_daily_loss_pct=req.max_daily_loss_pct,
        max_weekly_loss_pct=req.max_weekly_loss_pct,
        max_trades_per_day=req.max_trades_per_day,
    )

    # 4. Run Backtest (Partitioned or Full)
    if req.run_partitioned_split and len(df_features) >= 150:
        results = ChronologicalSplitter.run_partitioned_backtest(
            df_candles_with_features=df_features,
            initial_balance=req.initial_balance,
            strategy_config=strat_cfg,
            cost_config=cost_cfg,
            risk_config=risk_cfg
        )
    else:
        engine = OfflineBacktestEngine(
            initial_balance=req.initial_balance,
            strategy_config=strat_cfg,
            cost_config=cost_cfg,
            risk_config=risk_cfg
        )
        raw_res = engine.run(df_features)
        metrics = PerformanceMetricsCalculator.calculate(
            initial_balance=req.initial_balance,
            trades=raw_res["trades"],
            equity_curve=raw_res["equity_curve"]
        )
        results = {
            "partitions": None,
            "full_dataset": {
                "total_bars": len(df_features),
                "metrics": metrics,
                "trades": raw_res["trades"],
                "equity_curve": raw_res["equity_curve"]
            },
            "disclaimer": "Full dataset evaluation without chronological splitting."
        }

    results["strategy_config"] = strat_cfg.to_dict()
    results["cost_scenario"] = cost_cfg.to_dict()
    results["risk_config"] = risk_cfg.to_dict()
    results["quality_report"] = quality_report

    # Cache run result for export
    run_id = str(uuid.uuid4())
    _RESULTS_CACHE[run_id] = {
        "results": results,
        "quality_report": quality_report
    }
    results["run_id"] = run_id

    return results


@router.post("/sensitivity")
def run_sensitivity_analysis(req: OfflineRunRequest):
    """
    Executes parameter sensitivity grid across ATR stop multiplier and Risk-Reward ratio.
    Evaluated strictly on Development and Validation partitions.
    """
    if req.dataset_id and req.dataset_id in _DATASET_CACHE:
        df_features = _DATASET_CACHE[req.dataset_id]["df"]
    else:
        df_candles = mt5_adapter.get_candles(symbol="EURUSD", timeframe="M15", count=800)
        df_features = FeaturePipeline.calculate_features(df_candles)

    strat_cfg = StrategyConfig(
        fast_ema_period=req.fast_ema_period,
        slow_ema_period=req.slow_ema_period,
        rsi_period=req.rsi_period,
        rsi_long_min=req.rsi_long_min,
        rsi_long_max=req.rsi_long_max,
        rsi_short_min=req.rsi_short_min,
        rsi_short_max=req.rsi_short_max,
    )

    cost_cfg = (
        CostModelPresets.elevated() if req.cost_scenario == "Elevated"
        else (CostModelPresets.stressed() if req.cost_scenario == "Stressed" else CostModelPresets.normal())
    )

    grid_results = ChronologicalSplitter.run_sensitivity_grid(
        df_candles_with_features=df_features,
        base_strategy_config=strat_cfg,
        cost_config=cost_cfg,
        initial_balance=req.initial_balance
    )

    return {"grid": grid_results}


@router.get("/report/pdf")
def download_pdf_report(run_id: str = Query(...)):
    """Generates and downloads PDF research report."""
    if run_id not in _RESULTS_CACHE:
        raise HTTPException(status_code=404, detail="Backtest run not found or expired.")

    entry = _RESULTS_CACHE[run_id]
    pdf_path = str(BACKTEST_CACHE_DIR / f"backtest_report_{run_id}.pdf")

    BacktestReportGenerator.generate_pdf(
        results=entry["results"],
        data_quality=entry["quality_report"],
        output_path=pdf_path
    )

    return FileResponse(
        path=pdf_path,
        filename=f"TradePilot_Backtest_Report_{run_id[:8]}.pdf",
        media_type="application/pdf"
    )


@router.get("/report/csv")
def download_csv_trades(run_id: str = Query(...)):
    """Generates and downloads CSV trade log."""
    if run_id not in _RESULTS_CACHE:
        raise HTTPException(status_code=404, detail="Backtest run not found or expired.")

    entry = _RESULTS_CACHE[run_id]
    results = entry["results"]
    trades = results.get("trades") or results.get("full_dataset", {}).get("trades", [])

    csv_data = BacktestReportGenerator.export_csv_trades(trades)

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tradepilot_trades_{run_id[:8]}.csv"}
    )


# Backward Compatibility Route
@router.post("/run")
def run_backtest_legacy(req: BacktestRequest):
    """
    Legacy backtest route for backward compatibility with existing tests and UI.
    """
    try:
        candles_df = mt5_adapter.get_candles(
            symbol=req.symbol,
            timeframe=req.timeframe,
            count=req.start_bars
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch historical candles: {e}")

    engine = BacktestEngine(
        initial_balance=req.initial_balance,
        spread_pips=req.spread_pips,
        slippage_points=req.slippage_points,
        commission_per_lot=req.commission_per_lot
    )

    results = engine.run_backtest(
        df_candles=candles_df,
        strategy_mode=req.strategy_name,
        symbol=req.symbol
    )

    return results
