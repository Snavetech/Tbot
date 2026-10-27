"""
Unit tests for Independent Deterministic Risk Engine
"""
import pytest
from backend.app.config import settings
from backend.app.services.risk_engine import RiskEngine


def test_position_sizing_rounds_down(fresh_risk_engine):
    """Test that volume calculation correctly rounds DOWN to broker volume step (0.01)"""
    symbol_spec = {
        "tick_size": 0.00001,
        "tick_value": 1.0,
        "volume_step": 0.01,
        "volume_min": 0.01,
        "volume_max": 50.0,
    }
    account_equity = 10000.0
    entry_price = 1.08500
    stop_loss = 1.08250  # 25 pips = 250 ticks. Cost per lot = $250.
    # Risk budget: 0.25% of 10000 = $25.
    # Raw volume: 25 / 250 = 0.10 lot.

    vol, risk_amount, sl_pips, err = fresh_risk_engine.calculate_position_size(
        account_equity=account_equity,
        entry_price=entry_price,
        stop_loss=stop_loss,
        symbol_spec=symbol_spec
    )

    assert err is None
    assert vol == 0.10
    assert risk_amount <= 25.0
    assert sl_pips == 25.0


def test_zero_or_invalid_stop_loss_distance(fresh_risk_engine):
    """Test rejection when stop loss distance is zero or negative"""
    symbol_spec = {
        "tick_size": 0.00001,
        "tick_value": 1.0,
        "volume_step": 0.01,
        "volume_min": 0.01,
        "volume_max": 50.0,
    }

    vol, risk_amount, sl_pips, err = fresh_risk_engine.calculate_position_size(
        account_equity=10000.0,
        entry_price=1.08500,
        stop_loss=1.08500,  # Zero distance!
        symbol_spec=symbol_spec
    )
    assert err is not None
    assert "Zero or invalid" in err
    assert vol == 0.0


def test_minimum_lot_risk_budget_rejection(fresh_risk_engine):
    """Test that if the minimum valid lot exceeds the risk budget, the trade is rejected"""
    symbol_spec = {
        "tick_size": 0.00001,
        "tick_value": 1.0,
        "volume_step": 0.01,
        "volume_min": 0.10,  # High min lot
        "volume_max": 50.0,
    }
    # Tiny account equity: $1,000. 0.25% risk budget = $2.50.
    # Stop distance: 100 pips = 1000 ticks.
    # Cost for 0.10 lot = 0.10 * 1000 * 1.0 = $100.
    # $100 > $2.50 -> Must reject!
    vol, risk_amount, sl_pips, err = fresh_risk_engine.calculate_position_size(
        account_equity=1000.0,
        entry_price=1.08500,
        stop_loss=1.07500,
        symbol_spec=symbol_spec
    )

    assert err is not None
    assert "exceeds risk budget" in err
    assert vol == 0.0


def test_daily_loss_limit_triggers_lock(fresh_risk_engine, test_db):
    """Test that breaching max daily loss percentage triggers safety lock"""
    from datetime import datetime, timezone
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fresh_risk_engine._last_day_reset = today_str
    fresh_risk_engine._daily_baseline_equity = 10000.0
    # Current equity dropped to 9850 (1.5% loss >= 1.0% limit)
    account_info = {"equity": 9850.0, "free_margin": 9850.0}
    signal = {"entry_price": 1.08500, "stop_loss": 1.08250, "signal_type": "BUY"}
    symbol_spec = {"tick_size": 0.00001, "tick_value": 1.0, "volume_step": 0.01, "volume_min": 0.01, "volume_max": 50.0}

    result = fresh_risk_engine.evaluate_order_risk(
        signal=signal,
        account_info=account_info,
        symbol_spec=symbol_spec,
        current_spread_pips=1.2,
        open_positions=[],
        db=test_db
    )

    assert not result.is_approved
    assert "Daily loss limit breached" in result.rejection_reason
    assert fresh_risk_engine.is_locked


def test_consecutive_losses_triggers_lock(fresh_risk_engine, test_db):
    """Test that 3 consecutive losses activate safety pause"""
    assert not fresh_risk_engine.is_locked

    fresh_risk_engine.record_trade_result(-25.0, db=test_db)
    assert not fresh_risk_engine.is_locked

    fresh_risk_engine.record_trade_result(-24.5, db=test_db)
    assert not fresh_risk_engine.is_locked

    fresh_risk_engine.record_trade_result(-26.0, db=test_db)
    # 3 consecutive losses!
    assert fresh_risk_engine.is_locked
    assert "maximum consecutive losses" in fresh_risk_engine.lock_reason


def test_manual_unlock_after_review(fresh_risk_engine):
    """Test explicit manual unlock clears lock and resets counters"""
    fresh_risk_engine._is_locked = True
    fresh_risk_engine._lock_reason = "Test lock"
    fresh_risk_engine._consecutive_losses = 3

    success, msg = fresh_risk_engine.unlock("supervisor_user")
    assert success
    assert not fresh_risk_engine.is_locked
    assert fresh_risk_engine._consecutive_losses == 0


def test_max_trades_per_day_limit(fresh_risk_engine, test_db):
    """Test rejection when maximum trades per day is reached"""
    from datetime import datetime, timezone
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fresh_risk_engine._last_day_reset = today_str
    fresh_risk_engine._trades_today_count = settings.MAX_TRADES_PER_DAY  # e.g. 5
    account_info = {"equity": 10000.0, "free_margin": 10000.0}
    signal = {"entry_price": 1.08500, "stop_loss": 1.08250, "signal_type": "BUY"}
    symbol_spec = {"tick_size": 0.00001, "tick_value": 1.0, "volume_step": 0.01, "volume_min": 0.01, "volume_max": 50.0}

    result = fresh_risk_engine.evaluate_order_risk(
        signal=signal,
        account_info=account_info,
        symbol_spec=symbol_spec,
        current_spread_pips=1.2,
        open_positions=[],
        db=test_db
    )
    assert not result.is_approved
    assert "Daily trade limit reached" in result.rejection_reason


def test_spread_filter_rejection(fresh_risk_engine, test_db):
    """Test order rejection when current spread exceeds MAX_SPREAD_PIPS"""
    account_info = {"equity": 10000.0, "free_margin": 10000.0}
    signal = {"entry_price": 1.08500, "stop_loss": 1.08250, "signal_type": "BUY"}
    symbol_spec = {"tick_size": 0.00001, "tick_value": 1.0, "volume_step": 0.01, "volume_min": 0.01, "volume_max": 50.0}

    # Spread is 3.5 pips > 2.5 pips maximum
    result = fresh_risk_engine.evaluate_order_risk(
        signal=signal,
        account_info=account_info,
        symbol_spec=symbol_spec,
        current_spread_pips=3.5,
        open_positions=[],
        db=test_db
    )
    assert not result.is_approved
    assert "exceeds maximum allowed" in result.rejection_reason
