# TradePilot AI — System Architecture & Component Design

This document details the internal design, quantitative pipelines, safety circuit breakers, and execution workflows of **TradePilot AI**.

---

## 1. High-Level System Topology

```
+---------------------------------------------------------------------------------+
|                                React Frontend                                   |
|       (Lightweight Charts, Dark Fintech Design System, 7 Specialized Pages)     |
+---------------------------------------------------------------------------------+
                                       ▲
                                       │ HTTP / REST (/api/v1/*)
                                       ▼
+---------------------------------------------------------------------------------+
|                               FastAPI Backend                                   |
|   (Lifespan Management, Background Decision Loop, Pydantic Schemas, Security)   |
+---------------------------------------------------------------------------------+
           │                                │                            │
           ▼                                ▼                            ▼
+--------------------+            +--------------------+        +-----------------+
| Market Data Engine |            | Strategy Engine &  |        | Deterministic   |
| (Tickers, Candles, |----------->| Quantitative ML    |------->| Risk Engine     |
| Indicators, Regimes|            | (Trend/Range/Wait) |        | (0.25%, 1% Cap) |
+--------------------+            +--------------------+        +-----------------+
           ▲                                                             │
           │                                                             ▼
           │                                                    +-----------------+
           │                                                    | Execution       |
           │                                                    | Gateway         |
           │                                                    +-----------------+
           │                                                             │
           ▼                                                             ▼
+---------------------------------------------------------------------------------+
|                           MetaTrader 5 Windows API                              |
|          (Account Trade Mode Demo Verification, Order Checks, Ticks)            |
+---------------------------------------------------------------------------------+
```

---

## 2. Core Subsystems

### A. MT5 Adapter (`backend/app/services/mt5_adapter.py`)
- Interfaces directly with the official MetaTrader 5 Python library on Windows.
- **Symbol Discovery:** Queries `mt5.symbols_get("*EURUSD*")` to discover broker-specific suffixes (e.g., `EURUSDm` on Exness trial accounts).
- **Market Watch Auto-Selection:** Calls `mt5.symbol_select(symbol, True)` so quotes are ingested without requiring the user to manually find the symbol in terminal Market Watch.
- **Demo Verification Safeguard:** Enforces `account_info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO`. If a live account is detected, immediately terminates execution.
- **Comment Length Sanitization:** Restricts order comments to 31 characters (`comment[:31]`) to prevent broker error `-2`.
- **Automatic Mock Fallback:** If MT5 is not running or unavailable, seamlessly switches to an in-memory paper trading simulation.

### B. Market Data & Indicators (`backend/app/services/market_data.py`)
- Calculates mathematical indicators over pandas DataFrames without future leakage:
  - **EMAs:** 20, 50, and 200 periods.
  - **RSI:** 14-period Wilder smoothing.
  - **ATR:** 14-period True Range for dynamic volatility stops.
  - **Bollinger Bands:** 20-period moving average with 2.0 standard deviations.
  - **Pivot Points:** Classic Floor High/Low/Close support and resistance.
- **Regime Classifier:** Classifies market state into:
  - `trending`: Clear EMA alignment ($EMA_{20} > EMA_{50} > EMA_{200}$) with directional slope.
  - `ranging`: Price oscillating within Bollinger Bands with flat EMAs and moderate RSI.
  - `high_volatility`: ATR exceeds 1.8x the 50-period average ATR.
  - `uncertain`: Mixed indicator readings.

### C. Strategy Engine (`backend/app/strategies/`)
- Evaluates candidate trading signals based on regime classification:
  - **Trend-Following:** Enters on pullback or breakout in the direction of the EMA trend with RSI momentum confirmation.
  - **Range-Bound (Mean Reversion):** Buys near lower Bollinger Band or key Support when RSI is oversold; sells near upper band or Resistance when RSI is overbought. Disables during high volatility or breakouts.
  - **Adaptive Orchestrator:** Dispatches to the appropriate strategy according to current market regime. Recommends `WAIT` when conditions are ambiguous.

### D. Deterministic Risk Engine (`backend/app/services/risk_engine.py`)
TradePilot AI strictly prevents over-leveraging through deterministic capital protection:
1. **Fixed Position Sizing:**
   $$\text{Risk Amount (\$) } = \text{Account Equity} \times 0.0025 \quad (0.25\%)$$
   $$\text{Lots} = \frac{\text{Risk Amount}}{\text{Stop Loss Pips} \times \text{Pip Value per Lot}}$$
   Volume is always rounded down (`math.floor(lots / step) * step`) to prevent fractional over-allocation.
2. **Daily Loss Limit (1.0% Hard Cap):**
   Calculates daily loss against day-start balance. If cumulative daily loss reaches 1.0%, the engine triggers a persistent risk lock and halts all new order evaluations.
3. **Weekly Loss Limit (3.0% Hard Cap):**
   Drawdown over the rolling week is capped at 3.0%.
4. **Consecutive Losses Lock:**
   Halts trading upon reaching 3 consecutive losing trades.
5. **Spread Protection:**
   Rejects trades if current broker spread exceeds 2.5 pips.
6. **Frequency Filter:**
   Caps trades at 5 executions per calendar day.

### E. Execution Gateway (`backend/app/services/execution_gateway.py`)
- Centralized point for all order lifecycle events:
  - **Idempotency:** Generates and tracks UUIDv4 `client_order_id` in database before sending request to MT5.
  - **Pre-execution Check:** Calls `mt5.order_check` prior to submission.
  - **Position Reconciliation:** Periodically polls MT5 open positions, matches against database records, and detects when a position is closed externally (e.g. SL/TP hit on broker server) to record realized PnL.
  - **Emergency Liquidation:** `emergency_flatten` method liquidates all open positions with market orders upon confirmation.

### F. Reporting & Analytics (`backend/app/reports/`)
- Computes comprehensive institutional metrics: Win Rate, Profit Factor, Gross Profit/Loss, Net PnL, Max Drawdown %, and Expectancy.
- Produces downloadable **PDF Reports** via ReportLab with formatted financial tables and data limitation disclaimers.
- Produces downloadable **CSV Exports** of all trade history.

---

## 3. Finite State Machine (BotState)

```
        +--------------+
        |     INIT     |
        +--------------+
               │
               ▼
        +--------------+
        |  CONNECTING  |
        +--------------+
               │
               ▼
        +--------------+ ◄────────────────────────┐
        |     IDLE     |                          │
        +--------------+                          │
          │          ▲                            │
    start │          │ stop                       │
          ▼          │                            │
        +--------------+      pause         +--------------+
        |   RUNNING    | ──────────────────>|    PAUSED    |
        +--------------+ <──────────────────+--------------+
               │              resume
  error / lock │
               ▼
        +--------------+
        | ERROR / LOCK |
        +--------------+
```

States and permissions:
- `IDLE`: Connected to MT5, monitoring positions, no new order evaluation.
- `RUNNING`: Actively ingests market data, evaluates AI strategies, and submits eligible orders.
- `PAUSED`: Temporarily stopped by user; open positions are still monitored and protected.
- `SAFE_STOP`: Halted new entries while allowing open trades to run to their defined SL/TP.
- `ERROR / SAFE_STOP`: Circuit breaker triggered (e.g. daily loss limit or consecutive losses). Requires manual review before resuming.
