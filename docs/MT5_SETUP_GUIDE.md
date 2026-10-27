# MetaTrader 5 Setup & Demo Account Guide

This guide walks you through setting up MetaTrader 5 on Windows to run TradePilot AI in **Demo-Only** mode.

---

## 1. Install MetaTrader 5 on Windows

1. Download MetaTrader 5 for Windows from your preferred broker (e.g. [Exness](https://www.exness.com/), [IC Markets](https://www.icmarkets.com/), or official [MetaQuotes](https://www.metatrader5.com/)).
2. Run the installer and complete the setup wizard.
3. Launch the desktop terminal once installed.

---

## 2. Open a Free Demo Account

1. In the MT5 desktop menu, click **File** -> **Open an Account**.
2. Search for your broker (e.g. `Exness Technologies Ltd` or `MetaQuotes Software Corp.`).
3. Select **Open a demo account to trade virtual money without risk**.
4. Enter your details and select:
   - Account Type: Standard Demo (or Trial)
   - Deposit: 10,000 USD (recommended for standard testing)
   - Leverage: 1:100 to 1:200
5. Note down your **Login number**, **Password**, and **Server name** (e.g., `Exness-MT5Trial10`).

---

## 3. Enable Algorithmic Trading in MT5

For Python to interact with your MT5 terminal:
1. In MT5, navigate to **Tools** -> **Options** (or press `Ctrl+O`).
2. Click the **Expert Advisors** tab.
3. Check the box: **Allow Algorithmic Trading**.
4. (Optional) You may uncheck "Disable algorithmic trading when the account has been changed".
5. Click **OK**.

---

## 4. Configure TradePilot AI `.env`

Open your [`.env`](file:///c:/Users/Ismail/Downloads/Tbot/.env) file in the project root:

```ini
TRADING_MODE=demo
LIVE_TRADING_ENABLED=false

# Enter your MT5 Demo credentials
MT5_LOGIN=81879914
MT5_SERVER=Exness-MT5Trial10
MT5_PASSWORD=your_demo_password

# Symbol Configuration (supports broker suffixes like EURUSDm)
ALLOWED_SYMBOLS=EURUSD,EURUSDm
DEFAULT_SYMBOL=EURUSD
```

> **Note:** If your MT5 terminal is already open and logged in on your Windows desktop, TradePilot AI connects automatically to the active terminal session even if `MT5_PASSWORD` is left blank!

---

## 5. Verify the Connection

We provide an automated verification script that tests:
- Desktop MT5 terminal connection
- Verification that the account is strictly in **DEMO** mode
- Broker symbol discovery and Market Watch selection
- Live EUR/USD tick and candle ingestion
- Broker pre-trade order check (`order_check`)

Run the verification script:
```powershell
.\venv\Scripts\python backend/tests/verify_demo_integration.py
```

Expected output:
```
======================================================================
  TRADEPILOT AI - METATRADER 5 DEMO INTEGRATION TEST
======================================================================
1. MT5 Terminal Connection... [OK] Connected to desktop terminal
2. Account Verification...
   Account Login: #81879914
   Trade Mode: DEMO (0)
   Server: Exness-MT5Trial10
   Company: Exness Technologies Ltd
   [OK] Demo Account Confirmed! (Live Trading is BLOCKED)
3. Symbol Resolution...
   Resolved EURUSD -> EURUSDm
   Selected into Market Watch: True
4. Ingesting Real-Time Quote...
   EURUSDm | Bid: 1.08412 | Ask: 1.08424 | Spread: 1.2 pips
5. Fetching Recent Candles...
   Fetched 10 M15 candles from MT5.
6. Performing Order Check Validation...
   Broker order_check: return code 0 (Check passed)
======================================================================
  [PASSED_ALL_CHECKS] MetaTrader 5 Demo Integration Verified!
======================================================================
```
