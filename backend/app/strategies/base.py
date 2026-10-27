"""
Base Strategy interface and Signal data structures
"""
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import pandas as pd


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"


@dataclass
class SignalResult:
    signal_type: SignalType
    symbol: str
    strategy_name: str
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float = 1.5
    strategy_version: str = "v1.0"
    market_regime: str = "uncertain"
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    invalidation_conditions: List[str] = field(default_factory=list)
    reasoning_summary: str = "No setup identified"


class BaseStrategy(ABC):
    """Abstract Strategy Interface"""

    def __init__(self, name: str, version: str = "v1.0"):
        self.name = name
        self.version = version

    @abstractmethod
    def evaluate(
        self,
        symbol: str,
        df_m15: pd.DataFrame,
        df_h1: Optional[pd.DataFrame] = None,
        current_spread_pips: float = 1.2
    ) -> SignalResult:
        """
        Evaluate strategy on closed candles.
        Must return SignalResult (with WAIT if no valid setup exists).
        """
        pass
