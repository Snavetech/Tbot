"""
Deterministic Position Sizing & Capital Protection Model
Enforces strict 0.25% equity risk sizing, daily/weekly loss limits,
consecutive loss circuit-breaker pauses, and daily trade frequency limits.
"""
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import math


@dataclass
class RiskConfig:
    risk_per_trade_pct: float = 0.25
    max_combined_open_risk_pct: float = 0.50
    max_daily_loss_pct: float = 1.0
    max_weekly_loss_pct: float = 3.0
    max_trades_per_day: int = 5
    consecutive_losses_limit: int = 3
    consecutive_losses_reset_daily: bool = True  # If True, resets pause on 00:00 UTC day boundary
    contract_size: float = 100000.0  # 1 standard lot = 100,000 EUR
    pip_value_per_lot: float = 10.0   # USD per pip on EUR/USD standard lot
    min_volume: float = 0.01
    max_volume: float = 10.0
    volume_step: float = 0.01

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_per_trade_pct": self.risk_per_trade_pct,
            "max_combined_open_risk_pct": self.max_combined_open_risk_pct,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "max_weekly_loss_pct": self.max_weekly_loss_pct,
            "max_trades_per_day": self.max_trades_per_day,
            "consecutive_losses_limit": self.consecutive_losses_limit,
            "consecutive_losses_reset_daily": self.consecutive_losses_reset_daily,
            "contract_size": self.contract_size,
            "pip_value_per_lot": self.pip_value_per_lot,
            "min_volume": self.min_volume,
            "max_volume": self.max_volume,
            "volume_step": self.volume_step,
        }


class BacktestRiskManager:
    """
    Manages position sizing and evaluates deterministic risk limits during simulation.
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()

        # State tracking
        self.consecutive_losses = 0
        self.is_locked = False
        self.lock_reason: Optional[str] = None

        # Period baselines for daily and weekly loss calculations
        self.current_day_str: Optional[str] = None
        self.current_week_str: Optional[str] = None
        self.day_start_equity: float = 0.0
        self.week_start_equity: float = 0.0
        self.trades_today = 0

    def reset(self, initial_equity: float):
        """Reset risk manager state for a new simulation run."""
        self.consecutive_losses = 0
        self.is_locked = False
        self.lock_reason = None
        self.current_day_str = None
        self.current_week_str = None
        self.day_start_equity = initial_equity
        self.week_start_equity = initial_equity
        self.trades_today = 0

    def update_calendar_baselines(self, timestamp: int, current_equity: float):
        """
        Updates daily and weekly baselines on period boundaries.
        00:00 UTC triggers daily reset; Monday 00:00 UTC triggers weekly reset.
        """
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        day_str = dt.strftime("%Y-%m-%d")
        week_str = f"{dt.year}-W{dt.isocalendar()[1]:02d}"

        # Day transition
        if self.current_day_str != day_str:
            self.current_day_str = day_str
            self.day_start_equity = current_equity
            self.trades_today = 0
            
            # Check if Weekly loss limit is currently breached before unlocking daily states
            weekly_breached = False
            if self.week_start_equity > 0:
                w_loss_pct = ((self.week_start_equity - current_equity) / self.week_start_equity) * 100.0
                if w_loss_pct >= self.config.max_weekly_loss_pct:
                    weekly_breached = True
                    self.is_locked = True
                    self.lock_reason = f"Weekly loss limit reached: {w_loss_pct:.2f}% >= {self.config.max_weekly_loss_pct}%"

            if not weekly_breached:
                # Reset daily loss lock or daily consecutive loss pause upon new trading day
                if self.is_locked and self.lock_reason:
                    if "Daily loss" in self.lock_reason:
                        self.is_locked = False
                        self.lock_reason = None
                    elif self.config.consecutive_losses_reset_daily and (
                        "consecutive" in self.lock_reason.lower() or "paused" in self.lock_reason.lower()
                    ):
                        self.is_locked = False
                        self.lock_reason = None
                        self.consecutive_losses = 0
                elif self.config.consecutive_losses_reset_daily:
                    self.consecutive_losses = 0

        # Week transition
        if self.current_week_str != week_str:
            self.current_week_str = week_str
            self.week_start_equity = current_equity
            if self.is_locked and self.lock_reason and "Weekly loss" in self.lock_reason:
                self.is_locked = False
                self.lock_reason = None


    def calculate_lot_size(
        self,
        equity: float,
        stop_distance_pips: float
    ) -> Tuple[float, str]:
        """
        Calculates position volume deterministically from account equity:
        Risk ($) = Equity * 0.0025
        Lots = Risk / (Stop Loss pips * $10/pip)
        Rounded down to broker volume step (0.01).
        """
        if stop_distance_pips <= 0:
            return 0.0, "Invalid stop distance (<= 0)"

        risk_dollars = equity * (self.config.risk_per_trade_pct / 100.0)
        pip_risk_cost = stop_distance_pips * self.config.pip_value_per_lot

        raw_lots = risk_dollars / pip_risk_cost
        
        # Round down to volume step to prevent exceeding risk budget
        step = self.config.volume_step
        stepped_lots = math.floor(raw_lots / step) * step
        stepped_lots = round(stepped_lots, 4)

        if stepped_lots < self.config.min_volume:
            return 0.0, f"Calculated volume {stepped_lots} below broker minimum ({self.config.min_volume} lots)"

        final_lots = min(stepped_lots, self.config.max_volume)
        return final_lots, "OK"

    def check_trade_allowed(
        self,
        current_equity: float,
        open_risk_pct: float = 0.0
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluates circuit breakers:
        - Risk lock status
        - Consecutive losses limit
        - Daily loss limit (1.0% cap)
        - Weekly loss limit (3.0% cap)
        - Daily trade count limit (max 5)
        - Combined open risk limit (max 0.50%)
        """
        if self.is_locked:
            return False, f"Risk locked: {self.lock_reason}"

        # 1. Consecutive losses check
        if self.consecutive_losses >= self.config.consecutive_losses_limit:
            self.is_locked = True
            self.lock_reason = f"Consecutive loss limit reached ({self.consecutive_losses} >= {self.config.consecutive_losses_limit})"
            return False, self.lock_reason

        # 2. Daily loss limit check
        if self.day_start_equity > 0:
            daily_loss = self.day_start_equity - current_equity
            daily_loss_pct = (daily_loss / self.day_start_equity) * 100.0
            if daily_loss_pct >= self.config.max_daily_loss_pct:
                self.is_locked = True
                self.lock_reason = f"Daily loss limit reached: {daily_loss_pct:.2f}% >= {self.config.max_daily_loss_pct}%"
                return False, self.lock_reason

        # 3. Weekly loss limit check
        if self.week_start_equity > 0:
            weekly_loss = self.week_start_equity - current_equity
            weekly_loss_pct = (weekly_loss / self.week_start_equity) * 100.0
            if weekly_loss_pct >= self.config.max_weekly_loss_pct:
                self.is_locked = True
                self.lock_reason = f"Weekly loss limit reached: {weekly_loss_pct:.2f}% >= {self.config.max_weekly_loss_pct}%"
                return False, self.lock_reason

        # 4. Max daily trades count
        if self.trades_today >= self.config.max_trades_per_day:
            return False, f"Max trades today reached ({self.trades_today}/{self.config.max_trades_per_day})"

        # 5. Combined open risk check
        projected_risk = open_risk_pct + self.config.risk_per_trade_pct
        if projected_risk > self.config.max_combined_open_risk_pct:
            return False, f"Combined open risk ({projected_risk:.2f}%) exceeds limit ({self.config.max_combined_open_risk_pct}%)"

        return True, None

    def record_trade_result(self, net_pnl: float):
        """Updates consecutive loss streak and daily trade count."""
        self.trades_today += 1
        if net_pnl < 0:
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.config.consecutive_losses_limit:
                self.is_locked = True
                self.lock_reason = f"Paused after {self.consecutive_losses} consecutive losses"
        elif net_pnl > 0:
            self.consecutive_losses = 0
