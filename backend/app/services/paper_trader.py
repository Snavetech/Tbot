"""
Paper Trading Service: Live simulation on actual market data without submitting broker orders
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid

from backend.app.core.events import logger


class PaperTradingEngine:
    """
    Simulates paper trades locally using real-time price feeds.
    Completely isolated from MT5 demo execution.
    """

    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.closed_trades: List[Dict[str, Any]] = []

    def open_paper_position(
        self,
        symbol: str,
        side: str,
        volume: float,
        price: float,
        sl: float,
        tp: float,
        strategy: str
    ) -> Dict[str, Any]:
        """Record new simulated paper position"""
        pos_id = f"paper_{uuid.uuid4().hex[:8]}"
        pos = {
            "id": pos_id,
            "symbol": symbol,
            "side": side.upper(),
            "volume": volume,
            "entry_price": price,
            "current_price": price,
            "sl": sl,
            "tp": tp,
            "open_time": datetime.now(timezone.utc),
            "strategy": strategy,
            "profit": 0.0
        }
        self.positions[pos_id] = pos
        logger.info(f"[PAPER TRADING] Opened {side} {volume} {symbol} @ {price}")
        return pos

    def update_prices(self, bid: float, ask: float):
        """Update floating PnL and trigger SL/TP checks for paper positions"""
        for pos_id, pos in list(self.positions.items()):
            is_buy = pos["side"] == "BUY"
            cur_price = bid if is_buy else ask
            pos["current_price"] = cur_price

            pips = (cur_price - pos["entry_price"]) / 0.0001 if is_buy else (pos["entry_price"] - cur_price) / 0.0001
            pos["profit"] = round(pips * 10.0 * pos["volume"], 2)

            # Check SL
            if pos["sl"] > 0:
                if (is_buy and cur_price <= pos["sl"]) or (not is_buy and cur_price >= pos["sl"]):
                    self.close_paper_position(pos_id, "STOP_LOSS")
                    continue

            # Check TP
            if pos["tp"] > 0:
                if (is_buy and cur_price >= pos["tp"]) or (not is_buy and cur_price <= pos["tp"]):
                    self.close_paper_position(pos_id, "TAKE_PROFIT")
                    continue

        unrealized = sum(p["profit"] for p in self.positions.values())
        self.equity = round(self.balance + unrealized, 2)

    def close_paper_position(self, pos_id: str, reason: str = "MANUAL"):
        """Close simulated paper position"""
        if pos_id in self.positions:
            pos = self.positions.pop(pos_id)
            self.balance = round(self.balance + pos["profit"], 2)
            self.equity = self.balance

            trade_rec = {
                "id": pos_id,
                "symbol": pos["symbol"],
                "side": pos["side"],
                "volume": pos["volume"],
                "entry_price": pos["entry_price"],
                "exit_price": pos["current_price"],
                "open_time": pos["open_time"],
                "close_time": datetime.now(timezone.utc),
                "profit": pos["profit"],
                "exit_reason": reason,
                "strategy": pos["strategy"],
            }
            self.closed_trades.append(trade_rec)
            logger.info(f"[PAPER TRADING] Closed #{pos_id}. Profit: ${pos['profit']} ({reason})")


# Global singleton instance of PaperTradingEngine
paper_trader = PaperTradingEngine()
