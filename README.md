# TradePilot AI — Autonomous Forex Trading & Analytics Platform

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.3-61dafb.svg)](https://react.dev/)
[![MetaTrader 5](https://img.shields.io/badge/MetaTrader_5-Official_Python_API-orange.svg)](https://www.mql5.com/)
[![Mode](https://img.shields.io/badge/Safety-DEMO_ONLY_ENFORCED-green.svg)]()
[![Tests](https://img.shields.io/badge/Tests-32%2F32_Passing-brightgreen.svg)]()

**TradePilot AI** is an institutional-grade, AI-heavy autonomous Forex trading and analytics platform designed specifically for **EUR/USD**. It connects directly to **MetaTrader 5** via its official Windows Python API, ingests real-time ticks and multi-timeframe candles, runs leakage-free quantitative feature engineering, classifies market regimes, evaluates adaptive algorithmic strategies (Trend-Following & Range-Bound), enforces deterministic circuit-breaker risk rules (0.25% fixed position sizing, 1.0% daily cap), executes eligible orders in verified **demo accounts**, reconciles open positions, and generates institutional PDF & CSV performance reports.

---

## 🔒 Crucial Safety Architecture: DEMO-ONLY MODE

TradePilot AI includes hard-coded, multi-layer safeguards preventing live financial execution:
1. **Server-Level Validation:** `TRADING_MODE=demo` and `LIVE_TRADING_ENABLED=false` are enforced at startup.
2. **Terminal Account Mode Check:** Before every single order or connection attempt, the system verifies `account_info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO`. If a real/live account is detected, all trading functions throw an immediate, fatal `RuntimeError` and halt execution.
3. **Gateway Verification:** The `ExecutionGateway` refuses to place orders if the live safeguard flag is violated.
4. **Offline Mock Fallback:** If MetaTrader 5 is closed or not installed on Windows, TradePilot AI smoothly falls back to an in-memory realistic Forex paper-trading simulator, allowing full UI exploration without financial risk.

---

## 🚀 Key Features

- **Official MetaTrader 5 Integration:**
  - Auto-discovers broker symbol naming variations (e.g. `EURUSD`, `EURUSDm`, `EURUSD.raw`).
  - Automatic Market Watch symbol selection via `mt5.symbol_select`.
  - Enforces the broker 31-character comment limit (`comment[:31]`) to prevent `-2 (Invalid comment)` errors.
- **Leakage-Free Quantitative Engine:**
  - Real-time technical indicators: EMAs (20, 50, 200), RSI (14), ATR (14), Bollinger Bands (20, 2), and Pivot Points (Support/Resistance).
  - Multi-factor regime classifier: `trending`, `ranging`, `high_volatility`, and `uncertain`.
- **Adaptive Strategy Architecture:**
  - **Trend-Following:** Fast/Slow EMA crossovers + RSI momentum confirmation + ATR dynamic volatility stops.
  - **Range-Bound (Mean Reversion):** Bollinger Band envelope touches + RSI oversold/overbought mean reversion. Automatically disables during breakouts.
- **Deterministic Risk Management (RiskEngine):**
  - **Position Sizing:** Exactly **0.25%** account equity risked per trade, rounded down to broker volume steps (0.01 lots).
  - **Daily Loss Cap:** Hard circuit breaker halts trading when daily losses reach **1.0%**.
  - **Weekly Loss Cap:** Halted when weekly drawdown reaches **3.0%**.
  - **Consecutive Loss Pause:** Automatically locks new entries after **3 consecutive losses**.
  - **Spread Filter:** Blocks order execution if broker spread exceeds 2.5 pips.
  - **Trade Frequency Cap:** Enforces a maximum of 5 trades per day.
- **Idempotency & Position Reconciliation:**
  - UUIDv4 client order tracking prevents double fills.
  - Periodic reconciliation loop syncs broker terminal states with SQLite, detects external manual exits, SL/TP triggers, and records realized PnL.
- **Institutional Reporting & Export:**
  - Auto-generates structured daily, weekly, monthly, and all-time summaries.
  - Native **PDF Export** via ReportLab with tables, KPIs, and regulatory disclaimers.
  - Native **CSV Export** for trade logs.
- **Full-Featured Dark Fintech UI:**
  - Built with React, TypeScript, Vite, and Lightweight Charts.
  - 7 specialized pages:
    1. **Overview Dashboard:** Balance, equity, open risk, live quotes, regime, latest decision, and audit trail.
    2. **Trading Terminal:** Interactive candlestick chart, timeframe switcher (M1, M5, M15, H1, D1), indicator overlays, quote bar.
    3. **AI Strategy Intel:** Regime breakdown, model confidence gauge, expectancy, supporting/contradicting evidence lists, and invalidation rules.
    4. **Positions & Trades:** Open positions, closed trade history, order audit logs, manual close, and emergency liquidation.
    5. **Risk & Controls:** Circuit breaker progress bars, consecutive loss tracker, safety lock reset, and interactive position size calculator.
    6. **Reports & Analytics:** Performance KPIs (Win rate, Profit factor, Drawdown), strategy/regime attribution, and historical backtester simulator.
    7. **Settings & Health:** MT5 connection diagnostics, broker account details, bot state control (Start, Pause, Resume, Stop, Emergency Flatten), and audit log filter.

---

## 🛠️ System Prerequisites

- **Operating System:** Windows 10 or 11 (64-bit) — required for native MetaTrader 5 Python integration.
- **Python:** Python 3.10 to 3.13.
- **MetaTrader 5 Desktop Terminal:** Installed and logged into a **Demo Account** (e.g. Exness, MetaQuotes, IC Markets).
- **Node.js:** Node 18+ and npm for the frontend.

---

## ⚡ Quickstart Guide

### 1. Clone & Configure Environment
```bash
git clone <repository_url>
cd Tbot

# Copy example environment configuration
copy .env.example .env
```

Review [`.env`](file:///c:/Users/Ismail/Downloads/Tbot/.env):
```ini
TRADING_MODE=demo
LIVE_TRADING_ENABLED=false
MT5_LOGIN=81879914
MT5_SERVER=Exness-MT5Trial10
MT5_PASSWORD=
ALLOWED_SYMBOLS=EURUSD,EURUSDm
DEFAULT_SYMBOL=EURUSD
MAX_RISK_PER_TRADE_PCT=0.25
MAX_DAILY_LOSS_PCT=1.0
MAX_WEEKLY_LOSS_PCT=3.0
MAX_CONSECUTIVE_LOSSES=3
MAX_SPREAD_PIPS=2.5
```

### 2. Setup Python Virtual Environment & Install Dependencies
```powershell
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

### 3. Run Automated Pytest Suite
```powershell
.\venv\Scripts\pytest
```
*Expected: 32 passed tests in ~7 seconds.*

### 4. Verify Live Desktop MT5 Demo Connection
Ensure your MetaTrader 5 desktop terminal is open and logged into your demo account, then run:
```powershell
.\venv\Scripts\python backend/tests/verify_demo_integration.py
```
*Expected: `PASSED_ALL_CHECKS` confirming terminal connection, symbol resolution (`EURUSDm`), quote ingestion, and broker `order_check` validation.*

### 5. Launch Backend Server
```powershell
.\venv\Scripts\uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation is available at: `http://127.0.0.1:8000/docs`

### 6. Launch React Frontend
In a separate terminal:
```powershell
cd frontend
npm install
npm run dev
```
Open your browser at: `http://localhost:5173`

---

## 🧪 Testing Coverage

The automated test suite in [`backend/tests/`](file:///c:/Users/Ismail/Downloads/Tbot/backend/tests/) provides comprehensive regression protection:
- **`test_risk_engine.py`**: Validates 0.25% fixed position sizing, volume step round-down, zero/invalid stop-loss rejection, 1.0% daily loss lock, 3 consecutive losses lock, manual review unlock, 5 trades/day limit, and spread filters.
- **`test_execution_gateway.py`**: Verifies disconnection refusal, order idempotency, strict emergency flatten confirmation, and closed trade reconciliation.
- **`test_strategies.py`**: Tests insufficient data handling, high-volatility regime safety filters, and breakout range-bound deactivation.
- **`test_ai_analyst.py`**: Validates strict JSON output schema, rejection of unauthorized decisions/regimes, and deterministic rule-based fallback.
- **`test_reporting.py`**: Verifies ReportLab PDF generation, CSV exports, and period aggregation.
- **`test_backtester.py`**: Tests historical candle chronological replay and drawdown tracking.
- **`test_api_endpoints.py`**: Tests all FastAPI REST endpoints.

---

## 📚 Documentation Links

- [Architecture & Design Details](file:///c:/Users/Ismail/Downloads/Tbot/docs/ARCHITECTURE.md)
- [MT5 Setup & Demo Account Guide](file:///c:/Users/Ismail/Downloads/Tbot/docs/MT5_SETUP_GUIDE.md)
- [Broker Symbol Suffixes & Troubleshooting](file:///c:/Users/Ismail/Downloads/Tbot/docs/TROUBLESHOOTING.md)

---

## ⚖️ Legal & Financial Disclaimer

TradePilot AI is built strictly for educational, analytical, and research purposes in simulated **DEMO** environments. Foreign Exchange (Forex) and CFD trading involve substantial risk of capital loss and are not suitable for all investors. TradePilot AI does not provide financial or investment advice.
