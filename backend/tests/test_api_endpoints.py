"""
Integration and API endpoint tests
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

from backend.app.core.database import init_db
from backend.app.services.mt5_adapter import mt5_adapter

@pytest.fixture(autouse=True)
def setup_test_api():
    init_db()
    mt5_adapter.connect()
    yield

client = TestClient(app)


def test_health_endpoint():
    """Verify /api/health probe"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["mode"] == "demo"


def test_system_status_endpoint():
    """Verify /api/system/status response structure"""
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["trading_mode"] == "demo"
    assert data["live_trading_enabled"] is False
    assert "bot_state" in data


def test_market_ticker_endpoint():
    """Verify /api/market/ticker retrieves EURUSD quote"""
    response = client.get("/api/market/ticker?symbol=EURUSD")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "EURUSD"
    assert "bid" in data
    assert "ask" in data
    assert data["ask"] >= data["bid"]


def test_market_candles_endpoint():
    """Verify /api/market/candles returns candle sequence"""
    response = client.get("/api/market/candles?symbol=EURUSD&timeframe=M15&count=50")
    assert response.status_code == 200
    candles = response.json()
    assert len(candles) >= 10
    assert "open" in candles[0]
    assert "close" in candles[0]


def test_bot_state_endpoint():
    """Verify /api/bot/state reports current state"""
    response = client.get("/api/bot/state")
    assert response.status_code == 200
    data = response.json()
    assert "current_state" in data


def test_risk_status_endpoint():
    """Verify /api/risk/status returns deterministic safeguards"""
    response = client.get("/api/risk/status")
    assert response.status_code == 200
    data = response.json()
    assert data["max_risk_per_trade_pct"] == 0.25
    assert data["max_total_open_risk_pct"] == 0.50
    assert data["max_daily_loss_pct"] == 1.0


def test_backtest_run_endpoint():
    """Verify /api/backtest/run executes successfully"""
    payload = {
        "symbol": "EURUSD",
        "timeframe": "M15",
        "strategy_name": "all",
        "start_bars": 120,
        "initial_balance": 10000.0,
        "spread_pips": 1.2
    }
    response = client.post("/api/backtest/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "equity_curve" in data
