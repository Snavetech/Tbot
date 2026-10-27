"""
TradePilot AI Offline Backtesting & Quantitative Research Package
"""
from backend.app.backtesting.data_loader import HistoricalDataLoader, DataQualityReport
from backend.app.backtesting.features import FeaturePipeline
from backend.app.backtesting.strategy import BaselineTrendStrategy, StrategyConfig, SignalDecision
from backend.app.backtesting.costs import TransactionCostModel, CostModelConfig, CostModelPresets
from backend.app.backtesting.risk import BacktestRiskManager, RiskConfig
from backend.app.backtesting.engine import OfflineBacktestEngine
from backend.app.backtesting.splitter import ChronologicalSplitter
from backend.app.backtesting.metrics import PerformanceMetricsCalculator
from backend.app.backtesting.reports import BacktestReportGenerator

__all__ = [
    "HistoricalDataLoader",
    "DataQualityReport",
    "FeaturePipeline",
    "BaselineTrendStrategy",
    "StrategyConfig",
    "SignalDecision",
    "TransactionCostModel",
    "CostModelConfig",
    "CostModelPresets",
    "BacktestRiskManager",
    "RiskConfig",
    "OfflineBacktestEngine",
    "ChronologicalSplitter",
    "PerformanceMetricsCalculator",
    "BacktestReportGenerator"
]
