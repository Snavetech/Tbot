# TradePilot AI — Troubleshooting & Broker Conventions

This document covers common MetaTrader 5 integration scenarios, broker naming conventions, and troubleshooting steps.

---

## 1. Broker Symbol Suffixes (`EURUSDm`, `EURUSD.raw`, etc.)

Forex brokers frequently append characters to standard symbol names based on the account specification:
- **Exness Trial Accounts:** `EURUSDm` (Standard mini/trial suffix)
- **IC Markets Raw Accounts:** `EURUSD.raw`
- **Zero Spread Accounts:** `EURUSD_zero` or `EURUSDz`

### How TradePilot AI Handles This:
TradePilot AI features automated symbol discovery in `mt5_adapter.py`:
1. It queries `mt5.symbols_get("*EURUSD*")` to inspect all available variations offered by your broker.
2. It discovers matches such as `EURUSDm`.
3. It automatically selects the resolved symbol into the terminal's Market Watch using `mt5.symbol_select(symbol, True)`.
4. You can also explicitly configure your broker's symbol in `.env`:
   ```ini
   ALLOWED_SYMBOLS=EURUSD,EURUSDm
   DEFAULT_SYMBOL=EURUSD
   ```

---

## 2. Terminal Not Found / Quote Ingestion Failure

### Symptom:
`RuntimeError: Failed to get ticker for EURUSD: (-4, 'Terminal: Not found')`

### Cause:
The symbol exists in the broker's database but is **not active in the Market Watch window** in your MetaTrader 5 desktop terminal.

### Solution:
TradePilot AI automatically calls `mt5.symbol_select(symbol, True)`. However, if you see this error:
1. In the MT5 desktop terminal, open **View** -> **Market Watch** (or press `Ctrl+M`).
2. Right-click anywhere in Market Watch and select **Show All**.
3. Verify that your symbol (e.g. `EURUSDm`) is listed and actively receiving ticks.

---

## 3. MT5 Order Comment Argument Error (`-2, 'Invalid "comment" argument'`)

### Symptom:
`order_check error: (-2, 'Invalid "comment" argument')`

### Cause:
MetaTrader 5 enforces a strict **31-character limit** on the `comment` field of `MqlTradeRequest`. Any comment exceeding 31 characters is rejected with error code `-2`.

### Solution:
TradePilot AI automatically truncates all order comments to 31 characters:
```python
clean_comment = (request.comment or "TradePilot AI")[:31]
```
No manual action is required.

---

## 4. MT5 Is Closed or Not Installed on Windows

### Symptom:
You want to develop, test, or demonstrate TradePilot AI on a machine where MetaTrader 5 is temporarily closed or not installed.

### Solution:
TradePilot AI features an automatic **In-Memory Mock Fallback**:
- When `mt5.initialize()` fails, TradePilot AI outputs a warning and activates the mock adapter.
- The mock adapter simulates realistic EUR/USD ticks, M15 candle generation, order checks, and position tracking.
- The entire frontend, backtester, risk engine, and reporting suite function smoothly.
- To reconnect to real desktop MT5 at any time, start your MT5 terminal and click the **Reconnect** button in the top navigation bar or under **Settings & Health**.

---

## 5. Risk Safety Lock Triggered

### Symptom:
The top navigation bar displays a red badge: `RISK LOCKED`, and new orders are blocked.

### Cause:
One of TradePilot AI's deterministic circuit breakers was triggered:
- Daily loss reached 1.0%
- Weekly drawdown reached 3.0%
- 3 consecutive losing trades were recorded

### Solution:
1. Navigate to the **Risk & Controls** page.
2. Review the **Decision Log** and current loss percentage.
3. Once market conditions stabilize or the trading day resets, click **Reset Risk Lock**.
4. Confirm the prompt to reactivate order evaluation.
