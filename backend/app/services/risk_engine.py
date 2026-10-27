"""
Deterministic Independent Risk Management Engine
Applies strict mathematical position sizing, broker volume step rounding down,
portfolio-level drawdowns, and persistent safety locks.
"""
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.core.events import AuditService, logger
from backend.app.schemas.risk import RiskStatusResponse, RiskCheckResult


class RiskEngine:
    """
    Centralized, deterministic risk engine for TradePilot AI.
    No order can reach the execution gateway without approval from this service.
    """

    def __init__(self):
        # Runtime risk state
        self._is_locked: bool = False
        self._lock_reason: Optional[str] = None
        self._consecutive_losses: int = 0
        self._daily_baseline_equity: Optional[float] = None
        self._weekly_baseline_equity: Optional[float] = None
        self._last_day_reset: Optional[str] = None
        self._last_week_reset: Optional[str] = None
        self._trades_today_count: int = 0

    @property
    def is_locked(self) -> bool:
        return self._is_locked

    @property
    def lock_reason(self) -> Optional[str]:
        return self._lock_reason

    def unlock(self, authorized_by: str = "user_manual_review") -> Tuple[bool, str]:
        """Explicitly reset safety lock after authorized review"""
        self._is_locked = False
        self._lock_reason = None
        self._consecutive_losses = 0
        logger.info(f"Risk lock manually cleared by {authorized_by}")
        return True, "Risk safety lock unlocked successfully"

    def record_trade_result(self, net_pnl: float, db: Optional[Session] = None):
        """Record trade outcome to maintain consecutive loss counts and limits"""
        if net_pnl < 0:
            self._consecutive_losses += 1
            if self._consecutive_losses >= settings.MAX_CONSECUTIVE_LOSSES:
                self._is_locked = True
                self._lock_reason = (
                    f"Hit maximum consecutive losses ({self._consecutive_losses} >= "
                    f"{settings.MAX_CONSECUTIVE_LOSSES}). Trading paused."
                )
                AuditService.log_event(
                    db,
                    event_type="RISK_LOCK_ACTIVATED",
                    severity="WARNING",
                    message=self._lock_reason
                )
        else:
            self._consecutive_losses = 0

    def sync_baselines(self, current_equity: float):
        """Sync daily and weekly equity baselines at UTC rollover"""
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        week_str = f"{now.year}-W{now.isocalendar()[1]}"

        if self._last_day_reset is None:
            self._last_day_reset = today_str
            if self._daily_baseline_equity is None:
                self._daily_baseline_equity = current_equity

        elif self._last_day_reset != today_str:
            self._daily_baseline_equity = current_equity
            self._trades_today_count = 0
            self._last_day_reset = today_str

        if self._last_week_reset is None:
            self._last_week_reset = week_str
            if self._weekly_baseline_equity is None:
                self._weekly_baseline_equity = current_equity

        elif self._last_week_reset != week_str:
            self._weekly_baseline_equity = current_equity
            self._last_week_reset = week_str

    def calculate_position_size(
        self,
        account_equity: float,
        entry_price: float,
        stop_loss: float,
        symbol_spec: Dict[str, Any]
    ) -> Tuple[float, float, float, Optional[str]]:
        """
        Calculate maximum affordable volume rounded down to broker volume step.
        Returns: (approved_volume, risk_amount, stop_distance_pips, rejection_error)
        """
        stop_distance = abs(entry_price - stop_loss)
        if stop_distance <= 0.00001:
            return 0.0, 0.0, 0.0, "Zero or invalid stop-loss distance provided."

        tick_size = symbol_spec.get("tick_size", 0.00001)
        tick_value = symbol_spec.get("tick_value", 1.0)
        volume_step = symbol_spec.get("volume_step", 0.01)
        volume_min = symbol_spec.get("volume_min", 0.01)
        volume_max = symbol_spec.get("volume_max", 50.0)

        # Risk budget in currency (e.g. 0.25% of equity)
        risk_pct = settings.MAX_RISK_PER_TRADE_PCT
        risk_budget = account_equity * (risk_pct / 100.0)

        # Number of ticks in stop distance
        ticks = stop_distance / tick_size
        cost_per_lot = ticks * tick_value

        if cost_per_lot <= 0:
            return 0.0, 0.0, 0.0, "Cost per lot calculation resulted in non-positive value."

        raw_volume = risk_budget / cost_per_lot

        # Round DOWN to nearest valid volume step
        stepped_volume = math.floor(raw_volume / volume_step) * volume_step
        stepped_volume = round(stepped_volume, 2)

        # Check minimum lot constraint
        if stepped_volume < volume_min:
            min_lot_risk = volume_min * cost_per_lot
            if min_lot_risk > risk_budget:
                return (
                    0.0,
                    round(min_lot_risk, 2),
                    round(stop_distance / 0.0001, 1),
                    f"Minimum valid lot ({volume_min}) risk (${round(min_lot_risk, 2)}) "
                    f"exceeds risk budget (${round(risk_budget, 2)})."
                )
            stepped_volume = volume_min

        # Cap at maximum lot
        approved_volume = min(stepped_volume, volume_max)

        # Recalculate actual risk amount after volume rounding
        actual_risk_amount = round(approved_volume * cost_per_lot, 2)
        stop_distance_pips = round(stop_distance / 0.0001, 1)

        return approved_volume, actual_risk_amount, stop_distance_pips, None

    def evaluate_order_risk(
        self,
        signal: Dict[str, Any],
        account_info: Dict[str, Any],
        symbol_spec: Dict[str, Any],
        current_spread_pips: float,
        open_positions: List[Dict[str, Any]],
        db: Optional[Session] = None
    ) -> RiskCheckResult:
        """
        Evaluate full deterministic risk checks before allowing order execution.
        """
        equity = float(account_info.get("equity", 10000.0))
        self.sync_baselines(equity)

        rejection_reasons = []

        # 1. Safety Lock Check
        if self._is_locked:
            return RiskCheckResult(
                is_approved=False,
                approved_volume=0.0,
                requested_volume=0.0,
                risk_amount=0.0,
                risk_pct=0.0,
                stop_loss_distance_pips=0.0,
                rejection_reason=f"Risk engine safety lock active: {self._lock_reason}"
            )

        # 2. Daily Loss Limit Check
        if self._daily_baseline_equity and self._daily_baseline_equity > 0:
            daily_loss_amount = self._daily_baseline_equity - equity
            daily_loss_pct = max(0.0, (daily_loss_amount / self._daily_baseline_equity) * 100.0)
            if daily_loss_pct >= settings.MAX_DAILY_LOSS_PCT:
                self._is_locked = True
                self._lock_reason = (
                    f"Daily loss limit breached: {round(daily_loss_pct, 2)}% >= "
                    f"{settings.MAX_DAILY_LOSS_PCT}% limit."
                )
                AuditService.log_event(db, "RISK_LOCK_ACTIVATED", self._lock_reason, severity="ERROR")
                return RiskCheckResult(
                    is_approved=False,
                    approved_volume=0.0,
                    requested_volume=0.0,
                    risk_amount=0.0,
                    risk_pct=0.0,
                    stop_loss_distance_pips=0.0,
                    rejection_reason=self._lock_reason
                )

        # 3. Weekly Loss Limit Check
        if self._weekly_baseline_equity and self._weekly_baseline_equity > 0:
            weekly_loss_amount = self._weekly_baseline_equity - equity
            weekly_loss_pct = max(0.0, (weekly_loss_amount / self._weekly_baseline_equity) * 100.0)
            if weekly_loss_pct >= settings.MAX_WEEKLY_LOSS_PCT:
                self._is_locked = True
                self._lock_reason = (
                    f"Weekly loss limit breached: {round(weekly_loss_pct, 2)}% >= "
                    f"{settings.MAX_WEEKLY_LOSS_PCT}% limit."
                )
                AuditService.log_event(db, "RISK_LOCK_ACTIVATED", self._lock_reason, severity="ERROR")
                return RiskCheckResult(
                    is_approved=False,
                    approved_volume=0.0,
                    requested_volume=0.0,
                    risk_amount=0.0,
                    risk_pct=0.0,
                    stop_loss_distance_pips=0.0,
                    rejection_reason=self._lock_reason
                )

        # 4. Maximum Trades Per Day
        if self._trades_today_count >= settings.MAX_TRADES_PER_DAY:
            return RiskCheckResult(
                is_approved=False,
                approved_volume=0.0,
                requested_volume=0.0,
                risk_amount=0.0,
                risk_pct=0.0,
                stop_loss_distance_pips=0.0,
                rejection_reason=f"Daily trade limit reached: {self._trades_today_count}/{settings.MAX_TRADES_PER_DAY} trades taken."
            )

        # 5. Spread Check
        if current_spread_pips > settings.MAX_SPREAD_PIPS:
            return RiskCheckResult(
                is_approved=False,
                approved_volume=0.0,
                requested_volume=0.0,
                risk_amount=0.0,
                risk_pct=0.0,
                stop_loss_distance_pips=0.0,
                rejection_reason=f"Current spread ({current_spread_pips} pips) exceeds maximum allowed ({settings.MAX_SPREAD_PIPS} pips)."
            )

        # 6. Mandatory Protective Stop-Loss
        entry = float(signal.get("entry_price", 0.0))
        sl = float(signal.get("stop_loss", 0.0))
        sig_type = signal.get("signal_type", "").upper()

        if sl <= 0.0:
            return RiskCheckResult(
                is_approved=False,
                approved_volume=0.0,
                requested_volume=0.0,
                risk_amount=0.0,
                risk_pct=0.0,
                stop_loss_distance_pips=0.0,
                rejection_reason="Mandatory protective stop-loss missing (SL <= 0)."
            )

        if sig_type == "BUY" and sl >= entry:
            return RiskCheckResult(
                is_approved=False,
                approved_volume=0.0,
                requested_volume=0.0,
                risk_amount=0.0,
                risk_pct=0.0,
                stop_loss_distance_pips=0.0,
                rejection_reason=f"Invalid BUY stop-loss ({sl}) must be below entry ({entry})."
            )

        if sig_type == "SELL" and sl <= entry:
            return RiskCheckResult(
                is_approved=False,
                approved_volume=0.0,
                requested_volume=0.0,
                risk_amount=0.0,
                risk_pct=0.0,
                stop_loss_distance_pips=0.0,
                rejection_reason=f"Invalid SELL stop-loss ({sl}) must be above entry ({entry})."
            )

        # 7. Position Sizing
        vol, risk_amount, sl_pips, size_err = self.calculate_position_size(
            equity, entry, sl, symbol_spec
        )
        if size_err:
            return RiskCheckResult(
                is_approved=False,
                approved_volume=0.0,
                requested_volume=0.0,
                risk_amount=risk_amount,
                risk_pct=round((risk_amount / equity) * 100.0, 2) if equity > 0 else 0.0,
                stop_loss_distance_pips=sl_pips,
                rejection_reason=size_err
            )

        # 8. Combined Open Risk Check
        current_open_risk = 0.0
        for pos in open_positions:
            pos_entry = pos.get("price_open", 0.0)
            pos_sl = pos.get("sl", 0.0)
            if pos_sl > 0:
                pos_sl_dist = abs(pos_entry - pos_sl)
                ticks = pos_sl_dist / symbol_spec.get("tick_size", 0.00001)
                pos_risk = ticks * symbol_spec.get("tick_value", 1.0) * pos.get("volume", 0.01)
                current_open_risk += pos_risk

        new_total_open_risk_pct = ((current_open_risk + risk_amount) / equity) * 100.0
        if new_total_open_risk_pct > settings.MAX_TOTAL_OPEN_RISK_PCT:
            return RiskCheckResult(
                is_approved=False,
                approved_volume=vol,
                requested_volume=vol,
                risk_amount=risk_amount,
                risk_pct=round((risk_amount / equity) * 100.0, 2),
                stop_loss_distance_pips=sl_pips,
                rejection_reason=(
                    f"Combined open risk ({round(new_total_open_risk_pct, 2)}%) would exceed "
                    f"maximum allowed {settings.MAX_TOTAL_OPEN_RISK_PCT}%."
                )
            )

        # 9. Free Margin Check
        margin_required = (symbol_spec.get("contract_size", 100000.0) * vol * entry) / 100.0
        free_margin = float(account_info.get("free_margin", equity))
        if margin_required > free_margin * 0.8:
            return RiskCheckResult(
                is_approved=False,
                approved_volume=vol,
                requested_volume=vol,
                risk_amount=risk_amount,
                risk_pct=round((risk_amount / equity) * 100.0, 2),
                stop_loss_distance_pips=sl_pips,
                rejection_reason=f"Insufficient free margin: requires ${round(margin_required, 2)}, available ${round(free_margin, 2)}."
            )

        # Approved!
        actual_risk_pct = round((risk_amount / equity) * 100.0, 3)
        return RiskCheckResult(
            is_approved=True,
            approved_volume=vol,
            requested_volume=vol,
            risk_amount=risk_amount,
            risk_pct=actual_risk_pct,
            stop_loss_distance_pips=sl_pips,
            rejection_reason=None,
            details={
                "margin_required": round(margin_required, 2),
                "combined_open_risk_pct": round(new_total_open_risk_pct, 2),
            }
        )

    def get_status(
        self,
        account_info: Dict[str, Any],
        current_spread_pips: float,
        open_positions: List[Dict[str, Any]]
    ) -> RiskStatusResponse:
        """Return comprehensive live risk status for frontend and health checks"""
        equity = float(account_info.get("equity", 10000.0))
        balance = float(account_info.get("balance", 10000.0))
        free_margin = float(account_info.get("free_margin", equity))
        self.sync_baselines(equity)

        daily_loss_pct = 0.0
        if self._daily_baseline_equity and self._daily_baseline_equity > 0:
            daily_loss_pct = max(0.0, ((self._daily_baseline_equity - equity) / self._daily_baseline_equity) * 100.0)

        weekly_loss_pct = 0.0
        if self._weekly_baseline_equity and self._weekly_baseline_equity > 0:
            weekly_loss_pct = max(0.0, ((self._weekly_baseline_equity - equity) / self._weekly_baseline_equity) * 100.0)

        # Calculate current total open risk
        open_risk_dollars = 0.0
        for p in open_positions:
            open_p = p.get("price_open", 0.0)
            sl = p.get("sl", 0.0)
            if sl > 0:
                dist = abs(open_p - sl)
                open_risk_dollars += (dist / 0.00001) * 1.0 * p.get("volume", 0.01)

        open_risk_pct = round((open_risk_dollars / equity) * 100.0, 2) if equity > 0 else 0.0

        can_trade = (
            not self._is_locked
            and daily_loss_pct < settings.MAX_DAILY_LOSS_PCT
            and weekly_loss_pct < settings.MAX_WEEKLY_LOSS_PCT
            and self._trades_today_count < settings.MAX_TRADES_PER_DAY
            and current_spread_pips <= settings.MAX_SPREAD_PIPS
        )

        rejections = []
        if self._is_locked:
            rejections.append(f"Risk Lock: {self._lock_reason}")
        if daily_loss_pct >= settings.MAX_DAILY_LOSS_PCT:
            rejections.append(f"Daily loss reached {round(daily_loss_pct, 2)}%")
        if weekly_loss_pct >= settings.MAX_WEEKLY_LOSS_PCT:
            rejections.append(f"Weekly loss reached {round(weekly_loss_pct, 2)}%")
        if self._trades_today_count >= settings.MAX_TRADES_PER_DAY:
            rejections.append("Max daily trades reached")
        if current_spread_pips > settings.MAX_SPREAD_PIPS:
            rejections.append(f"Spread {current_spread_pips} > {settings.MAX_SPREAD_PIPS} pips")

        return RiskStatusResponse(
            max_risk_per_trade_pct=settings.MAX_RISK_PER_TRADE_PCT,
            max_total_open_risk_pct=settings.MAX_TOTAL_OPEN_RISK_PCT,
            current_open_risk_pct=open_risk_pct,
            daily_loss_pct=round(daily_loss_pct, 2),
            max_daily_loss_pct=settings.MAX_DAILY_LOSS_PCT,
            weekly_loss_pct=round(weekly_loss_pct, 2),
            max_weekly_loss_pct=settings.MAX_WEEKLY_LOSS_PCT,
            consecutive_losses=self._consecutive_losses,
            max_consecutive_losses=settings.MAX_CONSECUTIVE_LOSSES,
            trades_today=self._trades_today_count,
            max_trades_per_day=settings.MAX_TRADES_PER_DAY,
            is_locked=self._is_locked,
            lock_reason=self._lock_reason,
            account_equity=round(equity, 2),
            account_balance=round(balance, 2),
            free_margin=round(free_margin, 2),
            spread_pips=round(current_spread_pips, 1),
            max_spread_pips=settings.MAX_SPREAD_PIPS,
            can_trade=can_trade,
            rejection_reasons=rejections
        )


# Global singleton instance of RiskEngine
risk_engine = RiskEngine()
