"""
Persistent Engine Lifecycle and Background Trading Worker
Executes periodic market evaluation, position monitoring, and broker reconciliation.
"""
import asyncio
import time
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.core.database import SessionLocal
from backend.app.core.state_machine import BotStateMachine, BotState
from backend.app.core.events import AuditService, logger
from backend.app.services.mt5_adapter import mt5_adapter
from backend.app.services.market_data import MarketDataService
from backend.app.services.risk_engine import risk_engine
from backend.app.strategies.engine import strategy_engine
from backend.app.ml.ai_analyst import ai_analyst
from backend.app.services.execution_gateway import execution_gateway
from backend.app.models.models import (
    SignalRecord, AiAnalysisRecord, MarketSnapshot, AccountSnapshot, BotStateRecord
)


class EngineScheduler:
    """
    Manages the persistent background trading loop and state transitions.
    """

    def __init__(self):
        self.state_machine = BotStateMachine(BotState.DISCONNECTED)
        self._is_running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._last_evaluated_bar_time: Optional[int] = None
        self._last_reconcile_time: float = 0.0

    def start_worker(self):
        """Start async background worker loop"""
        if self._task is None or self._task.done():
            self._is_running = True
            self._task = asyncio.create_task(self._worker_loop())
            logger.info("EngineScheduler background worker started.")

    def stop_worker(self):
        """Stop background worker loop"""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("EngineScheduler background worker stopped.")

    async def _worker_loop(self):
        """Main periodic loop running in background"""
        logger.info("Background evaluation worker loop entered.")

        # Attempt initial demo connection
        try:
            connected, msg = mt5_adapter.connect()
            if connected:
                self.state_machine.transition_to(BotState.CONNECTED_DEMO, msg)
                self.state_machine.transition_to(BotState.READY, "System verified and ready")
            else:
                self.state_machine.transition_to(BotState.ERROR, f"Initial MT5 connection failed: {msg}")
        except Exception as e:
            logger.error(f"Error during initial MT5 connect: {e}")

        while self._is_running:
            try:
                # Prevent overlapping runs
                if not self.state_machine.is_evaluating:
                    self.state_machine.set_evaluating(True)
                    await self._evaluate_cycle()
                    self.state_machine.set_evaluating(False)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unhandled exception in trading cycle: {e}", exc_info=True)
                self.state_machine.set_evaluating(False)

            await asyncio.sleep(settings.EVALUATION_INTERVAL_SECONDS)

    async def _evaluate_cycle(self):
        """Single evaluation cycle"""
        db: Session = SessionLocal()
        try:
            # 1. Maintain Connection Health
            if not mt5_adapter.is_connected:
                if self.state_machine.current_state != BotState.DISCONNECTED:
                    try:
                        self.state_machine.transition_to(BotState.DISCONNECTED, "MT5 connection lost")
                    except Exception:
                        pass
                return

            # 2. Reconcile Positions and Monitor State
            now_sec = time.time()
            if now_sec - self._last_reconcile_time > settings.AUTO_RECONCILE_INTERVAL_SECONDS:
                execution_gateway.reconcile_positions(db)
                self._last_reconcile_time = now_sec

            # Snapshot Account
            try:
                acc_info = mt5_adapter.get_account_info()
                acc_snapshot = AccountSnapshot(
                    account_id=str(acc_info.get("login")),
                    balance=acc_info.get("balance", 10000.0),
                    equity=acc_info.get("equity", 10000.0),
                    margin=acc_info.get("margin", 0.0),
                    free_margin=acc_info.get("free_margin", 10000.0),
                    margin_level=acc_info.get("margin_level", 0.0),
                    currency=acc_info.get("currency", "USD"),
                    is_demo=acc_info.get("is_demo", True),
                    open_positions_count=len(mt5_adapter.get_open_positions()),
                )
                db.add(acc_snapshot)
                db.commit()
            except Exception as e:
                logger.warning(f"Could not record account snapshot: {e}")

            # Check if Risk Engine triggered a safety lock
            if risk_engine.is_locked and self.state_machine.current_state == BotState.RUNNING:
                self.state_machine.transition_to(
                    BotState.RISK_LOCKED,
                    f"Risk lock active: {risk_engine.lock_reason}"
                )

            # 3. If RUNNING: Evaluate strategy on latest closed M15 candle
            if self.state_machine.can_enter_trades():
                symbol = settings.DEFAULT_SYMBOL
                df_m15 = mt5_adapter.get_candles(symbol, timeframe=settings.DEFAULT_TIMEFRAME, count=120)
                df_h1 = mt5_adapter.get_candles(symbol, timeframe=settings.HTF_TIMEFRAME, count=60)

                if len(df_m15) < 30:
                    return

                # Check closed bar time to avoid redundant re-evaluation on same bar
                last_closed_bar_time = int(df_m15.iloc[-1]["time"])

                # Calculate indicators and classify regime
                df_m15_ind = MarketDataService.calculate_indicators(df_m15)
                regime, regime_details = MarketDataService.classify_regime(df_m15_ind)

                # Persist market snapshot
                latest_candle = df_m15_ind.iloc[-1]
                mkt_snapshot = MarketSnapshot(
                    symbol=symbol,
                    timeframe=settings.DEFAULT_TIMEFRAME,
                    open=latest_candle["open"],
                    high=latest_candle["high"],
                    low=latest_candle["low"],
                    close=latest_candle["close"],
                    volume=latest_candle["volume"],
                    atr=latest_candle.get("atr"),
                    rsi=latest_candle.get("rsi"),
                    ema_fast=latest_candle.get("ema_fast"),
                    ema_slow=latest_candle.get("ema_slow"),
                    regime=regime
                )
                db.add(mkt_snapshot)
                db.commit()

                # Evaluate Strategy Signal
                ticker = mt5_adapter.get_ticker(symbol)
                strategy_signal = strategy_engine.evaluate_market(
                    symbol=symbol,
                    df_m15=df_m15,
                    df_h1=df_h1,
                    current_spread_pips=ticker["spread_pips"]
                )

                # Evaluate AI Market Analysis
                ai_analysis = ai_analyst.analyze_market_state(
                    symbol=symbol,
                    regime=regime,
                    regime_details=regime_details,
                    signal=strategy_signal,
                    df_candles=df_m15_ind
                )

                # Record Signal in Database
                sig_id = f"sig_{int(time.time())}_{symbol}"
                sig_record = SignalRecord(
                    id=sig_id,
                    timestamp=datetime.now(timezone.utc),
                    symbol=symbol,
                    timeframe=settings.DEFAULT_TIMEFRAME,
                    strategy_name=strategy_signal.strategy_name,
                    signal_type=strategy_signal.signal_type.value,
                    entry_price=strategy_signal.entry_price,
                    stop_loss=strategy_signal.stop_loss,
                    take_profit=strategy_signal.take_profit,
                    risk_reward_ratio=strategy_signal.risk_reward_ratio,
                    strategy_version=strategy_signal.strategy_version,
                    is_executed=False,
                )
                db.add(sig_record)

                # Record AI Analysis in Database
                ai_record = AiAnalysisRecord(
                    signal_id=sig_id,
                    timestamp=datetime.now(timezone.utc),
                    symbol=symbol,
                    decision=ai_analysis.decision,
                    market_regime=ai_analysis.market_regime,
                    strategy=ai_analysis.strategy,
                    confidence=ai_analysis.confidence,
                    trade_expectancy=ai_analysis.trade_expectancy,
                    supporting_evidence=ai_analysis.supporting_evidence,
                    contradicting_evidence=ai_analysis.contradicting_evidence,
                    invalidation_conditions=ai_analysis.invalidation_conditions,
                    reasoning_summary=ai_analysis.reasoning_summary,
                    model_version=ai_analysis.model_version
                )
                db.add(ai_record)
                db.commit()

                # Only execute if both Strategy and AI agree on BUY/SELL and this candle has not been traded
                if (
                    strategy_signal.signal_type.value in {"BUY", "SELL"}
                    and ai_analysis.decision in {"BUY", "SELL"}
                    and strategy_signal.signal_type.value == ai_analysis.decision
                    and self._last_evaluated_bar_time != last_closed_bar_time
                ):
                    signal_payload = {
                        "id": sig_id,
                        "symbol": symbol,
                        "signal_type": strategy_signal.signal_type.value,
                        "strategy_name": strategy_signal.strategy_name,
                        "entry_price": strategy_signal.entry_price,
                        "stop_loss": strategy_signal.stop_loss,
                        "take_profit": strategy_signal.take_profit,
                    }

                    success, msg, details = execution_gateway.execute_demo_signal(signal_payload, db=db)
                    if success:
                        sig_record.is_executed = True
                        self._last_evaluated_bar_time = last_closed_bar_time
                        db.commit()
                        logger.info(f"Signal executed successfully: {msg}")
                    else:
                        sig_record.rejection_reason = msg
                        db.commit()
                        logger.warning(f"Signal execution refused: {msg}")

        finally:
            db.close()


# Global singleton instance of EngineScheduler
engine_scheduler = EngineScheduler()
