"""
Unit tests for Centralized Execution Gateway and Demo-Only Safeguards
"""
import pytest
from backend.app.config import settings
from backend.app.services.execution_gateway import ExecutionGateway
from backend.app.services.mt5_adapter import mt5_adapter
from backend.app.models.models import PositionRecord, TradeRecord


def test_refuse_when_disconnected(test_db):
    """Gateway must refuse order if MT5 is disconnected"""
    gateway = ExecutionGateway()
    was_connected = mt5_adapter._is_connected
    mt5_adapter._is_connected = False

    try:
        signal = {
            "id": "sig_test_1",
            "symbol": "EURUSD",
            "signal_type": "BUY",
            "entry_price": 1.08500,
            "stop_loss": 1.08250,
            "take_profit": 1.08900
        }
        success, msg, details = gateway.execute_demo_signal(signal, db=test_db)
        assert not success
        assert "disconnected" in msg.lower()
    finally:
        mt5_adapter._is_connected = was_connected


def test_duplicate_order_idempotency_prevention(test_db):
    """Gateway must reject duplicate signal executions using signal ID"""
    mt5_adapter.connect()
    gateway = ExecutionGateway()
    signal = {
        "id": "sig_idempotent_100",
        "symbol": "EURUSD",
        "signal_type": "BUY",
        "entry_price": 1.08500,
        "stop_loss": 1.08250,
        "take_profit": 1.08900
    }

    # First execution succeeds
    success, msg, details = gateway.execute_demo_signal(signal, db=test_db)
    assert success

    # Second immediate execution with same signal ID must be rejected!
    success2, msg2, details2 = gateway.execute_demo_signal(signal, db=test_db)
    assert not success2
    assert "Duplicate signal rejected" in msg2


def test_emergency_flatten_requires_exact_confirmation(test_db):
    """Emergency flatten must refuse if confirmation string is not exact"""
    gateway = ExecutionGateway()

    # Wrong confirmation
    success, msg, _ = gateway.emergency_flatten_all(
        confirmation="wrong_text",
        reason="test",
        db=test_db
    )
    assert not success
    assert "Confirmation string must match" in msg

    # Correct confirmation
    success2, msg2, closed = gateway.emergency_flatten_all(
        confirmation="FLATTEN_ALL_DEMO_POSITIONS",
        reason="Unit test emergency drill",
        db=test_db
    )
    assert success2


def test_position_reconciliation_detects_closed_trades(test_db):
    """Reconciliation reconciles local positions when closed on broker"""
    from datetime import datetime, timezone
    mt5_adapter.connect()
    gateway = ExecutionGateway()

    # Create local open position in DB
    pos = PositionRecord(
        ticket=999111,
        symbol="EURUSD",
        position_type="BUY",
        volume=0.10,
        open_price=1.08500,
        current_price=1.08700,
        sl=1.08200,
        tp=1.09000,
        profit=20.0,
        open_time=datetime.now(timezone.utc),
        status="OPEN"
    )
    test_db.add(pos)
    test_db.commit()

    # Ticket 999111 does not exist in mock MT5 broker positions
    # Reconcile should mark it as CLOSED and generate TradeRecord
    result = gateway.reconcile_positions(test_db)
    assert result["status"] == "reconciled"

    updated_pos = test_db.query(PositionRecord).filter(PositionRecord.ticket == 999111).first()
    assert updated_pos.status == "CLOSED"

    trade = test_db.query(TradeRecord).filter(TradeRecord.ticket == 999111).first()
    assert trade is not None
    assert trade.ticket == 999111
