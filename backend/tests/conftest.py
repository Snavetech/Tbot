"""
Pytest fixtures and configuration
Provides isolated in-memory test databases and mocked broker fixtures.
"""
import pytest
import time
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.services.mt5_adapter import MT5Adapter
from backend.app.services.risk_engine import RiskEngine
from backend.app.services.execution_gateway import ExecutionGateway


@pytest.fixture(autouse=True)
def force_mock_mt5_in_unit_tests():
    """Guarantee unit tests never touch real broker terminals or place real/demo orders"""
    from backend.app.services.mt5_adapter import mt5_adapter
    was_mock = mt5_adapter._is_mock
    was_conn = mt5_adapter._is_connected
    was_acc = mt5_adapter._account_info

    mt5_adapter._is_mock = True
    mt5_adapter._is_connected = True
    mt5_adapter._mock_balance = 10000.0
    mt5_adapter._mock_equity = 10000.0
    mt5_adapter._mock_positions.clear()
    mt5_adapter._mock_closed_trades.clear()
    mt5_adapter._account_info = {
        "login": 999888123,
        "trade_mode": "DEMO (Test Mock)",
        "balance": 10000.0,
        "equity": 10000.0,
        "margin": 0.0,
        "free_margin": 10000.0,
        "margin_level": 0.0,
        "currency": "USD",
        "server": "TradePilot-UnitTests",
        "company": "TradePilot AI Systems",
        "is_demo": True,
    }
    yield
    mt5_adapter._is_mock = was_mock
    mt5_adapter._is_connected = was_conn
    mt5_adapter._account_info = was_acc


@pytest.fixture
def test_db():
    """In-memory SQLite database for isolated test execution"""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def mock_mt5():
    """Isolated mock MT5 adapter instance"""
    adapter = MT5Adapter()
    adapter._is_connected = True
    adapter._is_mock = True
    adapter._mock_balance = 10000.0
    adapter._mock_equity = 10000.0
    adapter._account_info = {
        "login": 12345678,
        "trade_mode": "DEMO",
        "balance": 10000.0,
        "equity": 10000.0,
        "margin": 0.0,
        "free_margin": 10000.0,
        "margin_level": 0.0,
        "currency": "USD",
        "server": "TradePilot-TestDemo",
        "company": "TradePilot AI Testing",
        "is_demo": True,
    }
    return adapter


@pytest.fixture
def fresh_risk_engine():
    """Isolated fresh RiskEngine instance"""
    return RiskEngine()


@pytest.fixture
def sample_eurusd_candles():
    """Generates 150 realistic M15 EURUSD candlestick records"""
    np.random.seed(123)
    count = 150
    now = int(time.time())
    start_time = now - (count * 900)

    price = 1.08500
    rows = []
    returns = np.random.normal(0.00002, 0.0004, count)

    for i in range(count):
        open_p = price
        close_p = round(open_p * (1.0 + returns[i]), 5)
        high_p = round(max(open_p, close_p) + 0.0003, 5)
        low_p = round(min(open_p, close_p) - 0.0003, 5)
        vol = float(np.random.randint(200, 1000))

        rows.append({
            "time": start_time + (i * 900),
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "volume": vol
        })
        price = close_p

    return pd.DataFrame(rows)
