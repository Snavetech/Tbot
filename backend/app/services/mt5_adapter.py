"""
MetaTrader 5 Adapter with strict Demo-Only Verification,
Symbol Resolution, Market Data Ingestion, and Mock Fallback for Non-Terminal Testing.
"""
import time
import math
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
import numpy as np

from backend.app.config import settings
from backend.app.core.events import logger

# Try importing real MetaTrader5
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False


class MT5Adapter:
    """
    Dedicated MT5 Adapter providing safe broker communication.
    Refuses all operations if the connected account is not verified as DEMO.
    """

    TIMEFRAME_MAP = {
        "M1": getattr(mt5, "TIMEFRAME_M1", 1) if MT5_AVAILABLE else 1,
        "M5": getattr(mt5, "TIMEFRAME_M5", 5) if MT5_AVAILABLE else 5,
        "M15": getattr(mt5, "TIMEFRAME_M15", 15) if MT5_AVAILABLE else 15,
        "H1": getattr(mt5, "TIMEFRAME_H1", 16385) if MT5_AVAILABLE else 16385,
        "H4": getattr(mt5, "TIMEFRAME_H4", 16388) if MT5_AVAILABLE else 16388,
        "D1": getattr(mt5, "TIMEFRAME_D1", 16408) if MT5_AVAILABLE else 16408,
    }

    def __init__(self):
        self._is_connected: bool = False
        self._is_mock: bool = False
        self._account_info: Optional[Dict[str, Any]] = None
        self._symbol_cache: Dict[str, Dict[str, Any]] = {}
        self._last_heartbeat: Optional[datetime] = None

        # In-memory mock broker state for fallback/testing
        self._mock_balance: float = 10000.0
        self._mock_equity: float = 10000.0
        self._mock_positions: Dict[int, Dict[str, Any]] = {}
        self._mock_closed_trades: List[Dict[str, Any]] = []
        self._mock_ticket_counter: int = 700000
        self._mock_base_price: float = 1.08500
        self._mock_last_price_time: float = time.time()
        self._mock_candles: Dict[str, List[Dict[str, Any]]] = {}

        self._generate_initial_mock_candles()

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def is_mock(self) -> bool:
        return self._is_mock

    def connect(self) -> Tuple[bool, str]:
        """
        Connect to MetaTrader 5 terminal.
        If real MT5 is unavailable or fails to initialize, fallback to mock demo if configured.
        """
        if MT5_AVAILABLE and not self._is_mock:
            init_params = {}
            if settings.MT5_PATH:
                init_params["path"] = settings.MT5_PATH
            if settings.MT5_TIMEOUT_MS:
                init_params["timeout"] = settings.MT5_TIMEOUT_MS
            if settings.MT5_PORTABLE:
                init_params["portable"] = True

            logger.info("Attempting connection to MetaTrader 5 desktop terminal...")
            initialized = mt5.initialize(**init_params)

            if initialized:
                if settings.MT5_LOGIN and settings.MT5_PASSWORD and settings.MT5_SERVER:
                    logged_in = mt5.login(
                        login=settings.MT5_LOGIN,
                        password=settings.MT5_PASSWORD,
                        server=settings.MT5_SERVER
                    )
                    if not logged_in:
                        err = mt5.last_error()
                        logger.error(f"MT5 login failed: {err}")
                        mt5.shutdown()
                        return self._handle_connection_failure(f"MT5 login failed: {err}")

                # Verify Demo Account
                acc = mt5.account_info()
                if acc is None:
                    err = mt5.last_error()
                    mt5.shutdown()
                    return self._handle_connection_failure(f"Failed to get MT5 account info: {err}")

                # DEMO VERIFICATION CHECK
                # 0 = Demo, 1 = Contest, 2 = Real
                ACCOUNT_TRADE_MODE_DEMO = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
                if acc.trade_mode != ACCOUNT_TRADE_MODE_DEMO:
                    mt5.shutdown()
                    logger.critical(
                        f"CRITICAL SAFETY REFUSAL: Connected account #{acc.login} is a LIVE/CONTEST account. "
                        "TradePilot AI strictly prohibits live trading. Connection terminated."
                    )
                    return False, "SAFETY REFUSAL: Non-demo account detected. TradePilot AI requires a verified Demo account."

                self._is_connected = True
                self._is_mock = False
                self._account_info = {
                    "login": acc.login,
                    "trade_mode": "DEMO",
                    "balance": acc.balance,
                    "equity": acc.equity,
                    "margin": acc.margin,
                    "free_margin": acc.margin_free,
                    "margin_level": acc.margin_level,
                    "currency": acc.currency,
                    "server": acc.server,
                    "company": acc.company,
                    "is_demo": True,
                }
                self._last_heartbeat = datetime.now(timezone.utc)
                logger.info(f"Connected to MetaTrader 5 DEMO account #{acc.login} on {acc.server}")
                return True, f"Connected to MT5 Demo #{acc.login}"

            else:
                err = mt5.last_error()
                logger.warning(f"Could not connect to live MT5 terminal: {err}")
                return self._handle_connection_failure(f"MT5 terminal initialization error: {err}")

        return self._handle_connection_failure("MetaTrader5 python module not available on this platform")

    def _handle_connection_failure(self, reason: str) -> Tuple[bool, str]:
        """Fallback to simulated demo mode if enabled for local offline testing"""
        if settings.MT5_USE_MOCK_FALLBACK:
            logger.info("Initializing high-fidelity MT5 Mock Demo Adapter for offline / testing mode.")
            self._is_connected = True
            self._is_mock = True
            self._account_info = {
                "login": 999888123,
                "trade_mode": "DEMO (Simulated)",
                "balance": self._mock_balance,
                "equity": self._mock_equity,
                "margin": 0.0,
                "free_margin": self._mock_equity,
                "margin_level": 0.0,
                "currency": "USD",
                "server": "TradePilot-LocalDemo",
                "company": "TradePilot AI Systems",
                "is_demo": True,
            }
            self._last_heartbeat = datetime.now(timezone.utc)
            return True, f"Connected to MT5 Mock Demo (Reason: {reason})"
        else:
            self._is_connected = False
            return False, reason

    def disconnect(self):
        """Disconnect and gracefully release resources"""
        if self._is_connected and not self._is_mock and MT5_AVAILABLE:
            try:
                mt5.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down MT5: {e}")
        self._is_connected = False
        self._account_info = None
        logger.info("MT5 Adapter disconnected.")

    def get_account_info(self) -> Dict[str, Any]:
        """Return fresh demo account information"""
        if not self._is_connected:
            raise ConnectionError("MT5 is not connected")

        if not self._is_mock and MT5_AVAILABLE:
            acc = mt5.account_info()
            if acc is None:
                raise ConnectionError(f"Failed to fetch account info: {mt5.last_error()}")

            ACCOUNT_TRADE_MODE_DEMO = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
            if acc.trade_mode != ACCOUNT_TRADE_MODE_DEMO:
                self.disconnect()
                raise PermissionError("SAFETY BREACH: Non-demo account detected! Disconnected immediately.")

            self._account_info = {
                "login": acc.login,
                "trade_mode": "DEMO",
                "balance": float(acc.balance),
                "equity": float(acc.equity),
                "margin": float(acc.margin),
                "free_margin": float(acc.margin_free),
                "margin_level": float(acc.margin_level) if acc.margin_level else 0.0,
                "currency": acc.currency,
                "server": acc.server,
                "company": acc.company,
                "is_demo": True,
            }
            return self._account_info

        # Mock account updates
        unrealized_profit = sum(pos["profit"] for pos in self._mock_positions.values())
        self._mock_equity = self._mock_balance + unrealized_profit
        total_margin = sum(pos["margin"] for pos in self._mock_positions.values())
        free_margin = max(0.0, self._mock_equity - total_margin)
        margin_level = (self._mock_equity / total_margin * 100.0) if total_margin > 0 else 0.0

        self._account_info.update({
            "balance": round(self._mock_balance, 2),
            "equity": round(self._mock_equity, 2),
            "margin": round(total_margin, 2),
            "free_margin": round(free_margin, 2),
            "margin_level": round(margin_level, 2),
        })
        return self._account_info

    def resolve_symbol(self, symbol: str) -> str:
        """Resolve generic symbol to broker-specific symbol name using configured map or auto-discovery"""
        cleaned = symbol.strip().upper()
        if cleaned in settings.MT5_SYMBOL_MAP:
            target = settings.MT5_SYMBOL_MAP[cleaned]
            if not self._is_mock and MT5_AVAILABLE and self._is_connected:
                if mt5.symbol_info(target) is not None:
                    mt5.symbol_select(target, True)
                    return target
                # Mapped name does not exist on this specific broker; search dynamically
            else:
                return target

        if not self._is_mock and MT5_AVAILABLE and self._is_connected:
            # Check if direct name exists
            if mt5.symbol_info(cleaned) is not None:
                mt5.symbol_select(cleaned, True)
                return cleaned

            # Search broker symbols matching pattern
            try:
                matching = mt5.symbols_get(f"*{cleaned}*")
                if matching:
                    best_match = sorted(matching, key=lambda s: len(s.name))[0].name
                    settings.MT5_SYMBOL_MAP[cleaned] = best_match
                    mt5.symbol_select(best_match, True)
                    logger.info(f"Auto-discovered and selected broker symbol '{best_match}' for '{cleaned}'")
                    return best_match
            except Exception as e:
                logger.warning(f"Symbol search failed: {e}")

        return cleaned

    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Fetch symbol specifications (tick size, tick value, contract size, volume limits)"""
        resolved = self.resolve_symbol(symbol)

        if resolved in self._symbol_cache:
            return self._symbol_cache[resolved]

        if not self._is_mock and MT5_AVAILABLE:
            mt5.symbol_select(resolved, True)
            info = mt5.symbol_info(resolved)
            if info is None:
                raise ValueError(f"Symbol {resolved} not found on broker")
            if not info.visible:
                mt5.symbol_select(resolved, True)

            spec = {
                "name": info.name,
                "digits": info.digits,
                "point": info.point,
                "tick_size": info.trade_tick_size or info.point,
                "tick_value": info.trade_tick_value or 1.0,
                "contract_size": info.trade_contract_size or 100000.0,
                "volume_min": info.volume_min or 0.01,
                "volume_max": info.volume_max or 100.0,
                "volume_step": info.volume_step or 0.01,
                "spread_points": info.spread,
                "currency_base": info.currency_base,
                "currency_profit": info.currency_profit,
            }
            self._symbol_cache[resolved] = spec
            return spec

        # High-fidelity EURUSD mock specifications
        spec = {
            "name": resolved,
            "digits": 5,
            "point": 0.00001,
            "tick_size": 0.00001,
            "tick_value": 1.0,  # 1 pip on 0.1 lot = $1, on 1 lot = $10
            "contract_size": 100000.0,
            "volume_min": 0.01,
            "volume_max": 50.0,
            "volume_step": 0.01,
            "spread_points": 12,  # 1.2 pips
            "currency_base": "EUR",
            "currency_profit": "USD",
        }
        self._symbol_cache[resolved] = spec
        return spec

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch real-time Bid/Ask quote and freshness status"""
        resolved = self.resolve_symbol(symbol)

        if not self._is_mock and MT5_AVAILABLE:
            mt5.symbol_select(resolved, True)
            tick = mt5.symbol_info_tick(resolved)
            if tick is None:
                sinfo = mt5.symbol_info(resolved)
                if sinfo and sinfo.bid and sinfo.ask:
                    tick_bid = sinfo.bid
                    tick_ask = sinfo.ask
                    tick_time = int(time.time())
                else:
                    rates = mt5.copy_rates_from_pos(resolved, mt5.TIMEFRAME_M1, 0, 1)
                    if rates is not None and len(rates) > 0:
                        tick_bid = float(rates[0]["close"])
                        tick_ask = float(tick_bid + 0.00012)
                        tick_time = int(rates[0]["time"])
                    else:
                        raise RuntimeError(f"Failed to get ticker for {resolved}: {mt5.last_error()}")
            else:
                tick_bid = float(tick.bid)
                tick_ask = float(tick.ask)
                tick_time = int(tick.time)

            now_sec = time.time()
            is_stale = (now_sec - tick_time) > 300  # Stale if older than 5 minutes
            spread = round(tick_ask - tick_bid, 5)
            spread_pips = round(spread / 0.0001, 1)

            return {
                "symbol": resolved,
                "bid": tick_bid,
                "ask": tick_ask,
                "spread": spread,
                "spread_pips": spread_pips,
                "time": tick_time,
                "is_stale": is_stale,
            }

            return {
                "symbol": resolved,
                "bid": tick.bid,
                "ask": tick.ask,
                "spread": spread,
                "spread_pips": spread_pips,
                "time": int(tick.time),
                "is_stale": is_stale,
            }

        # Mock ticker generation with realistic micro-variations
        self._update_mock_price()
        spread_pips = 1.2
        spread = round(spread_pips * 0.0001, 5)
        bid = round(self._mock_base_price, 5)
        ask = round(bid + spread, 5)
        now_sec = int(time.time())

        return {
            "symbol": resolved,
            "bid": bid,
            "ask": ask,
            "spread": spread,
            "spread_pips": spread_pips,
            "time": now_sec,
            "is_stale": False,
        }

    def get_candles(self, symbol: str, timeframe: str = "M15", count: int = 200) -> pd.DataFrame:
        """
        Fetch historical closed candles for indicator and strategy evaluation.
        Columns: time, open, high, low, close, volume.
        """
        resolved = self.resolve_symbol(symbol)

        if not self._is_mock and MT5_AVAILABLE:
            tf = self.TIMEFRAME_MAP.get(timeframe.upper(), mt5.TIMEFRAME_M15)
            rates = mt5.copy_rates_from_pos(resolved, tf, 0, count)
            if rates is None or len(rates) == 0:
                raise RuntimeError(f"Failed to fetch rates for {resolved}: {mt5.last_error()}")

            df = pd.DataFrame(rates)
            df.rename(columns={"tick_volume": "volume"}, inplace=True)
            df["time"] = df["time"].astype(int)
            return df[["time", "open", "high", "low", "close", "volume"]]

        # Return mock candles dataframe
        if timeframe not in self._mock_candles or len(self._mock_candles[timeframe]) < count:
            self._generate_mock_candles(timeframe, count)

        df = pd.DataFrame(self._mock_candles[timeframe][-count:])
        return df

    def check_order(self, request: Dict[str, Any]) -> Tuple[bool, str]:
        """Run pre-order broker check before sending"""
        if not self._is_mock and MT5_AVAILABLE:
            res = mt5.order_check(request)
            if res is None:
                err = mt5.last_error()
                return False, f"order_check error: {err}"
            if res.retcode != 0:
                return False, f"Order check rejected by broker (code {res.retcode}): {res.comment}"
            return True, "Order check passed"

        # Mock pre-order validation
        volume = request.get("volume", 0.0)
        spec = self.get_symbol_info(request.get("symbol", "EURUSD"))
        if volume < spec["volume_min"]:
            return False, f"Volume {volume} is below broker minimum {spec['volume_min']}"
        if volume > spec["volume_max"]:
            return False, f"Volume {volume} exceeds broker maximum {spec['volume_max']}"
        if round(volume % spec["volume_step"], 4) not in {0.0, spec["volume_step"]}:
            return False, f"Volume {volume} does not conform to step {spec['volume_step']}"

        return True, "Mock order check passed"

    def send_order(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit demo order to broker. Strictly requires verified demo connection.
        """
        if not self._is_connected:
            raise ConnectionError("Cannot send order: MT5 is disconnected")

        # Double check demo status before execution
        acc = self.get_account_info()
        if not acc.get("is_demo", False):
            raise PermissionError("FATAL: Refused order submission. Account is not a verified demo account.")

        if not self._is_mock and MT5_AVAILABLE:
            result = mt5.order_send(request)
            if result is None:
                err = mt5.last_error()
                return {
                    "success": False,
                    "retcode": -1,
                    "comment": f"order_send returned None: {err}",
                    "order_id": None
                }

            TRADE_RETCODE_DONE = getattr(mt5, "TRADE_RETCODE_DONE", 10009)
            success = (result.retcode == TRADE_RETCODE_DONE)
            return {
                "success": success,
                "retcode": result.retcode,
                "comment": result.comment,
                "order_id": result.order if success else None,
                "price": result.price,
                "volume": result.volume
            }

        # Mock order execution
        self._mock_ticket_counter += 1
        ticket = self._mock_ticket_counter
        req_type = request.get("type", "BUY")
        order_type_str = "BUY" if req_type in {"BUY", 0} else "SELL"
        symbol = request.get("symbol", "EURUSD")
        volume = float(request.get("volume", 0.01))
        price = float(request.get("price", self._mock_base_price))
        sl = float(request.get("sl", 0.0))
        tp = float(request.get("tp", 0.0))

        # Margin requirement approx: 100,000 * volume * price / 100 leverage
        margin_required = (100000.0 * volume * price) / 100.0

        if margin_required > self._mock_equity:
            return {
                "success": False,
                "retcode": 10019,
                "comment": "No money / Insufficient margin",
                "order_id": None
            }

        position = {
            "ticket": ticket,
            "symbol": symbol,
            "type": order_type_str,
            "volume": volume,
            "price_open": price,
            "price_current": price,
            "sl": sl,
            "tp": tp,
            "swap": 0.0,
            "commission": round(-7.0 * volume, 2),
            "profit": 0.0,
            "margin": margin_required,
            "time": datetime.now(timezone.utc),
            "comment": request.get("comment", "TradePilot AI Demo")
        }
        self._mock_positions[ticket] = position

        logger.info(f"[MOCK BROKER] Order #{ticket} executed: {order_type_str} {volume} {symbol} @ {price}")
        return {
            "success": True,
            "retcode": 10009,
            "comment": "Done (Mock Demo Execution)",
            "order_id": ticket,
            "price": price,
            "volume": volume
        }

    def get_open_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all currently active positions"""
        if not self._is_connected:
            return []

        if not self._is_mock and MT5_AVAILABLE:
            resolved = self.resolve_symbol(symbol) if symbol else None
            positions = mt5.positions_get(symbol=resolved) if resolved else mt5.positions_get()
            if positions is None:
                return []

            result = []
            for pos in positions:
                pos_type = "BUY" if pos.type == 0 else "SELL"
                result.append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": pos_type,
                    "volume": pos.volume,
                    "price_open": pos.price_open,
                    "price_current": pos.price_current,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "swap": pos.swap,
                    "commission": getattr(pos, "commission", 0.0),
                    "profit": pos.profit,
                    "time": datetime.fromtimestamp(pos.time, tz=timezone.utc),
                    "comment": pos.comment,
                })
            return result

        # Mock positions update with current price
        self._update_mock_positions()
        res = []
        for p in self._mock_positions.values():
            if symbol and p["symbol"] != self.resolve_symbol(symbol):
                continue
            res.append({
                "ticket": p["ticket"],
                "symbol": p["symbol"],
                "type": p["type"],
                "volume": p["volume"],
                "price_open": p["price_open"],
                "price_current": p["price_current"],
                "sl": p["sl"],
                "tp": p["tp"],
                "swap": p["swap"],
                "commission": p["commission"],
                "profit": p["profit"],
                "time": p["time"],
                "comment": p["comment"],
            })
        return res

    def close_position(self, ticket: int, reason: str = "MANUAL_CLOSE") -> Tuple[bool, str]:
        """Close an open position at market price"""
        if not self._is_connected:
            return False, "Not connected to MT5"

        if not self._is_mock and MT5_AVAILABLE:
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                return False, f"Position #{ticket} not found on broker"

            pos = positions[0]
            close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            ticker = self.get_ticker(pos.symbol)
            price = ticker["bid"] if close_type == mt5.ORDER_TYPE_SELL else ticker["ask"]

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": ticket,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": close_type,
                "price": price,
                "deviation": settings.SLIPPAGE_TOLERANCE_POINTS,
                "magic": 1001,
                "comment": f"TradePilot Close: {reason}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            res = mt5.order_send(request)
            if res and res.retcode == getattr(mt5, "TRADE_RETCODE_DONE", 10009):
                return True, f"Position #{ticket} closed at {price}"
            return False, f"Failed to close #{ticket}: {res.comment if res else mt5.last_error()}"

        # Mock position close
        if ticket not in self._mock_positions:
            return False, f"Position #{ticket} not found in mock state"

        pos = self._mock_positions.pop(ticket)
        current_price = pos["price_current"]
        volume = pos["volume"]
        is_buy = pos["type"] == "BUY"

        # Calculate PnL
        pip_diff = (current_price - pos["price_open"]) / 0.0001 if is_buy else (pos["price_open"] - current_price) / 0.0001
        gross_pnl = round(pip_diff * 10.0 * volume, 2)
        net_pnl = round(gross_pnl + pos["commission"] + pos["swap"], 2)

        self._mock_balance += net_pnl
        self._mock_equity = self._mock_balance

        closed_record = {
            "ticket": ticket,
            "symbol": pos["symbol"],
            "trade_type": pos["type"],
            "volume": volume,
            "open_price": pos["price_open"],
            "close_price": current_price,
            "sl": pos["sl"],
            "tp": pos["tp"],
            "open_time": pos["time"],
            "close_time": datetime.now(timezone.utc),
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "commission": pos["commission"],
            "swap": pos["swap"],
            "slippage": 0.0,
            "exit_reason": reason,
        }
        self._mock_closed_trades.append(closed_record)
        logger.info(f"[MOCK BROKER] Position #{ticket} closed. Net PnL: ${net_pnl} ({reason})")
        return True, f"Position #{ticket} closed successfully"

    def get_trade_history(self, from_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Retrieve closed trades history"""
        if not self._is_mock and MT5_AVAILABLE:
            from_dt = from_date or (datetime.now(timezone.utc) - timedelta(days=30))
            deals = mt5.history_deals_get(from_dt, datetime.now(timezone.utc))
            if deals is None:
                return []

            res = []
            for d in deals:
                if d.entry == getattr(mt5, "DEAL_ENTRY_OUT", 1):  # Exit deals
                    deal_type = "SELL" if d.type == 0 else "BUY"
                    res.append({
                        "ticket": d.position_id,
                        "symbol": d.symbol,
                        "trade_type": deal_type,
                        "volume": d.volume,
                        "open_price": d.price,  # In deals MT5 provides execution price
                        "close_price": d.price,
                        "sl": 0.0,
                        "tp": 0.0,
                        "open_time": datetime.fromtimestamp(d.time, tz=timezone.utc),
                        "close_time": datetime.fromtimestamp(d.time, tz=timezone.utc),
                        "gross_pnl": d.profit,
                        "net_pnl": d.profit + d.commission + d.swap,
                        "commission": d.commission,
                        "swap": d.swap,
                        "slippage": 0.0,
                        "exit_reason": d.comment or "BROKER_EXECUTION",
                    })
            return res

        return list(self._mock_closed_trades)

    # -------------------------------------------------------------
    # Helper methods for mock broker emulation
    # -------------------------------------------------------------
    def _update_mock_price(self):
        """Simulate natural random walk on EURUSD price"""
        now = time.time()
        elapsed = now - self._mock_last_price_time
        if elapsed > 1.0:
            # Small random drift between -0.00008 and +0.00008
            drift = (random.random() - 0.495) * 0.00015
            self._mock_base_price = max(1.0400, min(1.1500, self._mock_base_price + drift))
            self._mock_last_price_time = now

    def _update_mock_positions(self):
        """Update floating PnL and check SL/TP for open positions"""
        self._update_mock_price()
        current_bid = self._mock_base_price
        current_ask = self._mock_base_price + 0.00012

        tickets_to_close = []
        for ticket, pos in list(self._mock_positions.items()):
            is_buy = (pos["type"] == "BUY")
            current_price = current_bid if is_buy else current_ask
            pos["price_current"] = current_price

            # Pip difference
            pips = (current_price - pos["price_open"]) / 0.0001 if is_buy else (pos["price_open"] - current_price) / 0.0001
            pos["profit"] = round(pips * 10.0 * pos["volume"], 2)

            # Check Stop-Loss
            if pos["sl"] > 0:
                if (is_buy and current_price <= pos["sl"]) or (not is_buy and current_price >= pos["sl"]):
                    tickets_to_close.append((ticket, "STOP_LOSS"))
                    continue

            # Check Take-Profit
            if pos["tp"] > 0:
                if (is_buy and current_price >= pos["tp"]) or (not is_buy and current_price <= pos["tp"]):
                    tickets_to_close.append((ticket, "TAKE_PROFIT"))
                    continue

        for ticket, reason in tickets_to_close:
            self.close_position(ticket, reason)

    def _generate_initial_mock_candles(self):
        """Generate realistic historical candle dataset for M15 and H1"""
        for tf in ["M1", "M5", "M15", "H1", "D1"]:
            self._generate_mock_candles(tf, count=300)

    def _generate_mock_candles(self, timeframe: str, count: int = 300):
        """Generates realistic candlestick series for backtesting and chart display"""
        interval_seconds = {
            "M1": 60,
            "M5": 300,
            "M15": 900,
            "H1": 3600,
            "H4": 14400,
            "D1": 86400,
        }.get(timeframe.upper(), 900)

        now = int(time.time())
        candles = []
        price = 1.08250

        # Start from `count` periods ago
        start_time = now - (count * interval_seconds)

        # Seed random for determinism if needed, but vary slightly
        np.random.seed(42)
        returns = np.random.normal(loc=0.00002, scale=0.00045, size=count)

        for i in range(count):
            candle_time = start_time + (i * interval_seconds)
            open_p = price
            ret = returns[i]
            close_p = round(open_p * (1.0 + ret), 5)
            spread = abs(ret * open_p)
            high_p = round(max(open_p, close_p) + abs(np.random.normal(0, 0.00025)), 5)
            low_p = round(min(open_p, close_p) - abs(np.random.normal(0, 0.00025)), 5)
            vol = round(float(np.random.randint(250, 1500)), 1)

            candles.append({
                "time": candle_time,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": vol
            })
            price = close_p

        self._mock_candles[timeframe] = candles
        self._mock_base_price = price


# Global singleton instance of MT5Adapter
mt5_adapter = MT5Adapter()
