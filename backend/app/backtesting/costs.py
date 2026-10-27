"""
Centralized Transaction Cost Modeling
Simulates realistic Forex transaction friction in a single documented place:
- Bid/Ask Spread (Historical or Assumed)
- Commission (Per standard lot round-turn)
- Slippage (Execution price deviation)
- Overnight Rollover Swap (Daily financing, including triple Wednesday convention)
Supports Normal-Cost, Elevated-Cost, and Stressed-Cost scenarios.
"""
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class CostModelConfig:
    name: str = "Normal"
    default_spread_pips: float = 1.2
    commission_per_lot_round_turn: float = 7.00
    slippage_pips: float = 0.5
    swap_long_per_lot_night: float = -2.50   # USD per night per lot
    swap_short_per_lot_night: float = -0.50  # USD per night per lot

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_name": self.name,
            "default_spread_pips": self.default_spread_pips,
            "commission_per_lot_round_turn": self.commission_per_lot_round_turn,
            "slippage_pips": self.slippage_pips,
            "swap_long_per_lot_night": self.swap_long_per_lot_night,
            "swap_short_per_lot_night": self.swap_short_per_lot_night,
        }


class CostModelPresets:
    """Standardized cost scenarios for sensitivity analysis."""

    @classmethod
    def normal(cls) -> CostModelConfig:
        return CostModelConfig(
            name="Normal",
            default_spread_pips=1.2,
            commission_per_lot_round_turn=7.00,
            slippage_pips=0.5,
            swap_long_per_lot_night=-2.50,
            swap_short_per_lot_night=-0.50
        )

    @classmethod
    def elevated(cls) -> CostModelConfig:
        return CostModelConfig(
            name="Elevated",
            default_spread_pips=2.0,
            commission_per_lot_round_turn=9.00,
            slippage_pips=1.0,
            swap_long_per_lot_night=-4.00,
            swap_short_per_lot_night=-1.50
        )

    @classmethod
    def stressed(cls) -> CostModelConfig:
        return CostModelConfig(
            name="Stressed",
            default_spread_pips=3.5,
            commission_per_lot_round_turn=12.00,
            slippage_pips=2.0,
            swap_long_per_lot_night=-6.00,
            swap_short_per_lot_night=-3.00
        )


class TransactionCostModel:
    """
    Applies transaction costs strictly in a single location to eliminate double-counting.
    """

    def __init__(self, config: Optional[CostModelConfig] = None):
        self.config = config or CostModelPresets.normal()

    def get_execution_entry_price(
        self,
        position_type: str,
        candle_open_price: float,
        bar_spread_pips: Optional[float] = None
    ) -> Tuple[float, float, float]:
        """
        Determines the entry execution price factoring in half-spread and slippage.
        Returns (executed_price, spread_cost_dollars, slippage_cost_dollars).
        """
        spread = bar_spread_pips if bar_spread_pips is not None else self.config.default_spread_pips
        spread_price = spread * 0.0001
        slippage_price = self.config.slippage_pips * 0.0001

        # For BUY: Enter at Ask = Candle Mid/Open + (Spread / 2) + Slippage
        # For SELL: Enter at Bid = Candle Mid/Open - (Spread / 2) - Slippage
        if position_type.upper() == "BUY":
            exec_price = candle_open_price + (spread_price / 2.0) + slippage_price
        else:
            exec_price = candle_open_price - (spread_price / 2.0) - slippage_price

        return round(exec_price, 5), spread, self.config.slippage_pips

    def get_execution_exit_price(
        self,
        position_type: str,
        target_price: float,
        is_stop_loss: bool,
        bar_spread_pips: Optional[float] = None
    ) -> Tuple[float, float, float]:
        """
        Determines exit price factoring in spread and slippage.
        Take profit limit orders typically experience zero adverse slippage,
        while stop-loss market orders suffer adverse slippage.
        """
        spread = bar_spread_pips if bar_spread_pips is not None else self.config.default_spread_pips
        spread_price = spread * 0.0001
        
        # Apply slippage only on market stop-loss exits, not limit take-profit
        slippage_price = (self.config.slippage_pips * 0.0001) if is_stop_loss else 0.0

        if position_type.upper() == "BUY":
            # To exit a BUY, we SELL at Bid = target - (Spread / 2) - Slippage
            exec_price = target_price - (spread_price / 2.0) - slippage_price
        else:
            # To exit a SELL, we BUY at Ask = target + (Spread / 2) + Slippage
            exec_price = target_price + (spread_price / 2.0) + slippage_price

        return round(exec_price, 5), spread, (self.config.slippage_pips if is_stop_loss else 0.0)

    def calculate_commission(self, volume_lots: float) -> float:
        """Total commission for round-turn order execution."""
        return round(self.config.commission_per_lot_round_turn * volume_lots, 2)

    def calculate_swap(
        self,
        position_type: str,
        volume_lots: float,
        entry_timestamp: int,
        exit_timestamp: int
    ) -> float:
        """
        Calculates financing rollover swap based on 21:00 UTC rollover crossing.
        Applies standard Forex 3x swap multiplier on Wednesday nights.
        """
        if exit_timestamp <= entry_timestamp:
            return 0.0

        dt_entry = datetime.fromtimestamp(entry_timestamp, tz=timezone.utc)
        dt_exit = datetime.fromtimestamp(exit_timestamp, tz=timezone.utc)

        # Count daily rollovers (crossing 21:00 UTC)
        total_nights = 0
        wednesday_nights = 0

        # Iterate by day
        cur = dt_entry.replace(hour=21, minute=0, second=0, microsecond=0)
        if cur <= dt_entry:
            cur = cur.fromtimestamp(cur.timestamp() + 86400, tz=timezone.utc)

        while cur <= dt_exit:
            total_nights += 1
            # In Forex, Wednesday rollover (weekday == 2) charges 3x to cover Saturday/Sunday
            if cur.weekday() == 2:
                wednesday_nights += 1
            cur = cur.fromtimestamp(cur.timestamp() + 86400, tz=timezone.utc)

        # Effective nights: each regular night is 1x, Wednesday is 3x (add 2 extra)
        effective_nights = total_nights + (wednesday_nights * 2)

        rate_per_lot = (
            self.config.swap_long_per_lot_night
            if position_type.upper() == "BUY"
            else self.config.swap_short_per_lot_night
        )

        return round(rate_per_lot * volume_lots * effective_nights, 2)
