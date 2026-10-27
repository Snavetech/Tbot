"""
Centralized Execution Gateway
The sole authorized execution path in TradePilot AI.
Strictly enforces server-side DEMO-ONLY verification, idempotency controls,
broker pre-checks, position reconciliation, and emergency flattening.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.services.mt5_adapter import mt5_adapter
from backend.app.services.risk_engine import risk_engine
from backend.app.core.events import AuditService, logger
from backend.app.models.models import OrderRecord, PositionRecord, SignalRecord, TradeRecord


class ExecutionGateway:
    """
    Centralized Execution Gateway.
    No strategy, AI, or scheduler may submit orders without passing through this gateway.
    """

    def __init__(self):
        # In-memory idempotency cache of recently processed signal IDs
        self._processed_signal_ids: Dict[str, datetime] = {}

    def execute_demo_signal(
        self,
        signal: Dict[str, Any],
        db: Session
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Executes an approved signal in the verified DEMO account.
        Performs all gate checks chronologically.
        """
        signal_id = signal.get("id") or str(uuid.uuid4())
        symbol = signal.get("symbol", settings.DEFAULT_SYMBOL)

        # 1. LIVE TRADING TECHNICAL BLOCK
        if settings.LIVE_TRADING_ENABLED or settings.TRADING_MODE != "demo":
            msg = "FATAL: Live trading execution attempted! Execution gateway blocked operation."
            AuditService.log_event(db, "EXECUTION_BLOCKED_LIVE_TRADING", msg, severity="CRITICAL")
            return False, msg, None

        # 2. MT5 Connectivity Check
        if not mt5_adapter.is_connected:
            msg = "Execution failed: MetaTrader 5 terminal is disconnected."
            AuditService.log_event(db, "EXECUTION_REJECTED_DISCONNECTED", msg, severity="WARNING")
            return False, msg, None

        # 3. Account Demo Verification Check
        try:
            account_info = mt5_adapter.get_account_info()
            if not account_info.get("is_demo", False):
                msg = "CRITICAL SAFETY REFUSAL: Connected account is NOT a verified demo account."
                AuditService.log_event(db, "SAFETY_REFUSAL_NOT_DEMO", msg, severity="CRITICAL")
                return False, msg, None
        except Exception as e:
            msg = f"Failed to verify demo account state: {e}"
            return False, msg, None

        # 4. Idempotency & Duplicate Order Prevention
        now = datetime.now(timezone.utc)
        if signal_id in self._processed_signal_ids:
            msg = f"Duplicate signal rejected: Signal ID {signal_id} has already been executed."
            return False, msg, None

        # Check existing open positions for duplicate entry on symbol
        existing_positions = mt5_adapter.get_open_positions(symbol)
        if len(existing_positions) >= 2:
            msg = f"Maximum position limit on symbol {symbol} reached ({len(existing_positions)} open)."
            return False, msg, None

        # 5. Symbol Resolution & Specification Check
        try:
            resolved_symbol = mt5_adapter.resolve_symbol(symbol)
            spec = mt5_adapter.get_symbol_info(symbol)
            ticker = mt5_adapter.get_ticker(symbol)
        except Exception as e:
            msg = f"Symbol resolution / market data failure for {symbol}: {e}"
            AuditService.log_event(db, "EXECUTION_SYMBOL_ERROR", msg, severity="ERROR")
            return False, msg, None

        # 6. Market Data Freshness / Stale Check
        if ticker.get("is_stale", False):
            msg = f"Market data for {symbol} is stale. Order execution refused."
            AuditService.log_event(db, "EXECUTION_STALE_DATA", msg, severity="WARNING")
            return False, msg, None

        # 7. Independent Risk Engine Gate Check
        risk_check = risk_engine.evaluate_order_risk(
            signal=signal,
            account_info=account_info,
            symbol_spec=spec,
            current_spread_pips=ticker["spread_pips"],
            open_positions=existing_positions,
            db=db
        )

        if not risk_check.is_approved:
            msg = f"Risk engine rejected order: {risk_check.rejection_reason}"
            AuditService.log_event(db, "RISK_REJECTION", msg, severity="WARNING", metadata={"signal_id": signal_id})
            return False, msg, None

        # 8. Broker Pre-Order Check
        order_type_str = signal.get("signal_type", "BUY").upper()
        # In MT5: 0 = Buy, 1 = Sell
        mt5_order_type = 0 if order_type_str == "BUY" else 1
        price = ticker["ask"] if order_type_str == "BUY" else ticker["bid"]
        volume = risk_check.approved_volume
        sl = float(signal.get("stop_loss", 0.0))
        tp = float(signal.get("take_profit", 0.0))

        client_order_id = f"TP_{int(now.timestamp())}_{uuid.uuid4().hex[:6]}"

        broker_request = {
            "action": 1,  # TRADE_ACTION_DEAL
            "symbol": resolved_symbol,
            "volume": volume,
            "type": mt5_order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": settings.SLIPPAGE_TOLERANCE_POINTS,
            "magic": 1001,
            "comment": f"TP_{signal.get('strategy_name', 'demo')}"[:31],
            "type_time": 0,  # GTC
            "type_filling": 1,  # IOC
        }

        check_passed, check_comment = mt5_adapter.check_order(broker_request)
        if not check_passed:
            msg = f"Broker pre-order check failed: {check_comment}"
            AuditService.log_event(db, "BROKER_CHECK_FAILED", msg, severity="ERROR")
            return False, msg, None

        # 9. Order Submission
        order_result = mt5_adapter.send_order(broker_request)
        self._processed_signal_ids[signal_id] = now

        # Record Order in DB
        order_record = OrderRecord(
            client_order_id=client_order_id,
            broker_order_id=order_result.get("order_id"),
            timestamp=now,
            signal_id=signal_id,
            symbol=symbol,
            order_type=order_type_str,
            volume=volume,
            requested_price=price,
            executed_price=order_result.get("price", price),
            sl=sl,
            tp=tp,
            status="FILLED" if order_result.get("success") else "REJECTED",
            retcode=order_result.get("retcode"),
            broker_comment=order_result.get("comment"),
        )
        db.add(order_record)

        # Update Risk Engine state
        risk_engine._trades_today_count += 1

        if order_result.get("success"):
            ticket = order_result.get("order_id")
            # Create local PositionRecord
            pos_record = PositionRecord(
                ticket=ticket or 0,
                symbol=symbol,
                position_type=order_type_str,
                volume=volume,
                open_price=order_result.get("price", price),
                current_price=order_result.get("price", price),
                sl=sl,
                tp=tp,
                open_time=now,
                status="OPEN",
                strategy_used=signal.get("strategy_name", "adaptive"),
                signal_id=signal_id
            )
            db.add(pos_record)
            db.commit()

            AuditService.log_event(
                db,
                "ORDER_EXECUTED_DEMO",
                f"Demo order #{ticket} executed: {order_type_str} {volume} {symbol} @ {price}",
                severity="INFO",
                metadata={"ticket": ticket, "client_order_id": client_order_id}
            )

            return True, f"Order #{ticket} executed successfully", {
                "ticket": ticket,
                "client_order_id": client_order_id,
                "price": price,
                "volume": volume,
            }
        else:
            db.commit()
            err_msg = f"Broker order submission rejected: {order_result.get('comment')} (Retcode: {order_result.get('retcode')})"
            AuditService.log_event(db, "ORDER_REJECTED", err_msg, severity="ERROR")
            return False, err_msg, None

    def emergency_flatten_all(
        self,
        confirmation: str,
        reason: str,
        db: Session
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Emergency flattening of all open demo positions with explicit confirmation.
        """
        if confirmation != "FLATTEN_ALL_DEMO_POSITIONS":
            return False, "Confirmation string must match 'FLATTEN_ALL_DEMO_POSITIONS'", []

        positions = mt5_adapter.get_open_positions()
        if not positions:
            return True, "No open positions to close.", []

        closed_results = []
        for pos in positions:
            ticket = pos["ticket"]
            success, comment = mt5_adapter.close_position(ticket, reason=f"EMERGENCY_FLATTEN: {reason}")
            closed_results.append({
                "ticket": ticket,
                "symbol": pos["symbol"],
                "success": success,
                "comment": comment
            })

            # Update local position record if exists
            local_pos = db.query(PositionRecord).filter(PositionRecord.ticket == ticket).first()
            if local_pos:
                local_pos.status = "CLOSED"

        db.commit()

        AuditService.log_event(
            db,
            "EMERGENCY_FLATTEN_EXECUTED",
            f"Emergency flatten executed for {len(positions)} positions. Reason: {reason}",
            severity="WARNING",
            metadata={"results": closed_results}
        )

        return True, f"Closed {len(positions)} positions.", closed_results

    def reconcile_positions(self, db: Session) -> Dict[str, Any]:
        """
        Reconciles local database positions with active broker positions.
        Handles restarts, external closes, and SL/TP fills.
        """
        if not mt5_adapter.is_connected:
            return {"status": "skipped", "reason": "MT5 not connected"}

        broker_positions = {p["ticket"]: p for p in mt5_adapter.get_open_positions()}
        local_positions = db.query(PositionRecord).filter(PositionRecord.status == "OPEN").all()

        closed_count = 0
        synced_count = 0

        for lp in local_positions:
            if lp.ticket not in broker_positions:
                # Position was closed at broker (e.g. SL or TP hit)
                lp.status = "CLOSED"
                closed_count += 1

                # Record in TradeRecord if not already present
                existing_trade = db.query(TradeRecord).filter(TradeRecord.ticket == lp.ticket).first()
                if not existing_trade:
                    trade_record = TradeRecord(
                        ticket=lp.ticket,
                        symbol=lp.symbol,
                        trade_type=lp.position_type,
                        volume=lp.volume,
                        open_price=lp.open_price,
                        close_price=lp.current_price,
                        sl=lp.sl,
                        tp=lp.tp,
                        open_time=lp.open_time,
                        close_time=datetime.now(timezone.utc),
                        gross_pnl=lp.profit,
                        net_pnl=lp.profit + lp.commission + lp.swap,
                        commission=lp.commission,
                        swap=lp.swap,
                        slippage=0.0,
                        exit_reason="SL_OR_TP_HIT",
                        strategy_used=lp.strategy_used or "adaptive",
                        signal_id=lp.signal_id
                    )
                    db.add(trade_record)
                    # Feed trade net PnL back into Risk Engine
                    risk_engine.record_trade_result(trade_record.net_pnl, db=db)
            else:
                # Sync live price & profit
                bp = broker_positions[lp.ticket]
                lp.current_price = bp["price_current"]
                lp.profit = bp["profit"]
                lp.swap = bp["swap"]
                synced_count += 1

        db.commit()
        return {
            "status": "reconciled",
            "broker_open_count": len(broker_positions),
            "local_closed_count": closed_count,
            "local_synced_count": synced_count
        }


# Global singleton instance of ExecutionGateway
execution_gateway = ExecutionGateway()
