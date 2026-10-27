"""
Explicitly Invoked Integration Test Procedure for Verifying Live MT5 Demo Connectivity
Run with: python backend/tests/verify_demo_integration.py
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.config import settings
from backend.app.services.mt5_adapter import mt5_adapter
from backend.app.services.risk_engine import risk_engine


def run_demo_integration_test():
    print("==================================================================")
    print(" TradePilot AI — Live MT5 Demo Connectivity & Verification Test   ")
    print("==================================================================")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Configured Default Symbol: {settings.DEFAULT_SYMBOL}")
    print(f"Trading Mode: {settings.TRADING_MODE}")
    print("------------------------------------------------------------------")

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stages": {},
        "overall_status": "PENDING"
    }

    # Stage 1: Terminal Connection
    print("\n[Stage 1/5] Testing MT5 Terminal Connection...")
    connected, conn_msg = mt5_adapter.connect()
    results["stages"]["connection"] = {
        "connected": connected,
        "is_mock": mt5_adapter.is_mock,
        "message": conn_msg
    }

    if not connected:
        print(f"[-] FAILED: Could not connect to MT5: {conn_msg}")
        results["overall_status"] = "FAILED_CONNECTION"
        _save_report(results)
        return

    print(f"[+] Connected! Mode: {'MOCK DEMO' if mt5_adapter.is_mock else 'NATIVE MT5'}")
    print(f"    Message: {conn_msg}")

    # Stage 2: Demo Account Verification
    print("\n[Stage 2/5] Verifying Account is Strictly DEMO...")
    try:
        acc = mt5_adapter.get_account_info()
        is_demo = acc.get("is_demo", False)
        results["stages"]["account_verification"] = {
            "login": acc.get("login"),
            "trade_mode": acc.get("trade_mode"),
            "server": acc.get("server"),
            "balance": acc.get("balance"),
            "equity": acc.get("equity"),
            "is_demo_verified": is_demo
        }
        if not is_demo:
            print("[-] CRITICAL SAFETY REFUSAL: Account is NOT a verified Demo account!")
            results["overall_status"] = "SAFETY_REFUSAL_NON_DEMO"
            _save_report(results)
            return

        print(f"[+] Demo Account Verified: #{acc.get('login')} on {acc.get('server')}")
        print(f"    Balance: ${acc.get('balance'):,.2f} | Equity: ${acc.get('equity'):,.2f}")
    except Exception as e:
        print(f"[-] Account verification error: {e}")
        results["overall_status"] = "FAILED_ACCOUNT_CHECK"
        _save_report(results)
        return

    # Stage 3: Symbol Resolution & Market Data Freshness
    print("\n[Stage 3/5] Resolving Symbol & Ingesting Ticker...")
    try:
        raw_symbol = settings.DEFAULT_SYMBOL
        resolved = mt5_adapter.resolve_symbol(raw_symbol)
        spec = mt5_adapter.get_symbol_info(raw_symbol)
        ticker = mt5_adapter.get_ticker(raw_symbol)

        results["stages"]["market_data"] = {
            "raw_symbol": raw_symbol,
            "resolved_symbol": resolved,
            "bid": ticker["bid"],
            "ask": ticker["ask"],
            "spread_pips": ticker["spread_pips"],
            "is_stale": ticker["is_stale"],
            "tick_size": spec["tick_size"],
            "volume_min": spec["volume_min"],
            "volume_step": spec["volume_step"],
        }

        print(f"[+] Resolved '{raw_symbol}' -> '{resolved}'")
        print(f"    Bid: {ticker['bid']} | Ask: {ticker['ask']} | Spread: {ticker['spread_pips']} pips")
        print(f"    Data Freshness: {'FRESH' if not ticker['is_stale'] else 'STALE'}")
    except Exception as e:
        print(f"[-] Symbol / market data error: {e}")
        results["overall_status"] = "FAILED_MARKET_DATA"
        _save_report(results)
        return

    # Stage 4: Candle Ingestion
    print("\n[Stage 4/5] Ingesting Closed Candles...")
    try:
        df = mt5_adapter.get_candles(raw_symbol, timeframe="M15", count=10)
        results["stages"]["candles"] = {
            "candle_count": len(df),
            "latest_close": float(df.iloc[-1]["close"]),
            "latest_time": int(df.iloc[-1]["time"])
        }
        print(f"[+] Ingested {len(df)} candles. Latest close: {df.iloc[-1]['close']}")
    except Exception as e:
        print(f"[-] Candle ingestion error: {e}")
        results["overall_status"] = "FAILED_CANDLES"
        _save_report(results)
        return

    # Stage 5: Broker Pre-Order Validation Check
    print("\n[Stage 5/5] Testing Broker Pre-Order Check (order_check)...")
    try:
        req = {
            "action": 1,
            "symbol": resolved,
            "volume": spec["volume_min"],
            "type": 0,  # BUY
            "price": ticker["ask"],
            "sl": round(ticker["ask"] - 0.0025, 5),
            "tp": round(ticker["ask"] + 0.0050, 5),
            "magic": 1001,
            "comment": "TradePilot Verify",
        }
        passed, check_comment = mt5_adapter.check_order(req)
        results["stages"]["order_check"] = {
            "passed": passed,
            "broker_comment": check_comment
        }
        if passed:
            print(f"[+] Broker pre-order check PASSED: {check_comment}")
            results["overall_status"] = "PASSED_ALL_CHECKS"
        else:
            print(f"[-] Broker pre-order check rejected: {check_comment}")
            results["overall_status"] = "FAILED_ORDER_CHECK"
    except Exception as e:
        print(f"[-] Order check error: {e}")
        results["overall_status"] = "FAILED_ORDER_CHECK"

    _save_report(results)
    print("\n==================================================================")
    print(f" Overall Verification Result: {results['overall_status']}")
    print(" Report written to: data/demo_verification_report.json")
    print("==================================================================")


def _save_report(results: dict):
    Path("./data").mkdir(parents=True, exist_ok=True)
    with open("./data/demo_verification_report.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    run_demo_integration_test()
