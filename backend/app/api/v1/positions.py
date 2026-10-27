"""
Positions, Orders, and Closed Trade History endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import verify_control_access
from backend.app.services.mt5_adapter import mt5_adapter
from backend.app.models.models import OrderRecord, TradeRecord, PositionRecord
from backend.app.schemas.trading import PositionResponse, OrderResponse, TradeResponse

router = APIRouter(prefix="", tags=["Positions & Trades"])


@router.get("/positions", response_model=List[PositionResponse])
def get_open_positions(db: Session = Depends(get_db)):
    """Fetch all open positions from broker & local tracking"""
    positions = mt5_adapter.get_open_positions()
    res = []
    for p in positions:
        local = db.query(PositionRecord).filter(PositionRecord.ticket == p["ticket"]).first()
        res.append(PositionResponse(
            ticket=p["ticket"],
            symbol=p["symbol"],
            position_type=p["type"],
            volume=p["volume"],
            open_price=p["price_open"],
            current_price=p["price_current"],
            sl=p["sl"],
            tp=p["tp"],
            swap=p["swap"],
            commission=p["commission"],
            profit=p["profit"],
            open_time=p["time"],
            status="OPEN",
            strategy_used=local.strategy_used if local else None,
            signal_id=local.signal_id if local else None,
        ))
    return res


@router.post("/positions/{ticket}/close", dependencies=[Depends(verify_control_access)])
def close_position(ticket: int, db: Session = Depends(get_db)):
    """Manually close a specific open demo position"""
    success, msg = mt5_adapter.close_position(ticket, reason="USER_MANUAL_DASHBOARD_CLOSE")
    if not success:
        raise HTTPException(status_code=400, detail=msg)

    local = db.query(PositionRecord).filter(PositionRecord.ticket == ticket).first()
    if local:
        local.status = "CLOSED"
        db.commit()

    return {"success": True, "message": msg}


@router.get("/orders", response_model=List[OrderResponse])
def get_orders(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Fetch order records submitted through execution gateway"""
    orders = db.query(OrderRecord).order_by(OrderRecord.timestamp.desc()).limit(limit).all()
    return [
        OrderResponse(
            client_order_id=o.client_order_id,
            broker_order_id=o.broker_order_id,
            timestamp=o.timestamp,
            symbol=o.symbol,
            order_type=o.order_type,
            volume=o.volume,
            requested_price=o.requested_price,
            executed_price=o.executed_price,
            sl=o.sl,
            tp=o.tp,
            status=o.status,
            retcode=o.retcode,
            broker_comment=o.broker_comment
        )
        for o in orders
    ]


@router.get("/trades", response_model=List[TradeResponse])
def get_trades(
    limit: int = Query(default=100, ge=1, le=500),
    strategy: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Searchable & filterable closed trades table"""
    query = db.query(TradeRecord)
    if strategy:
        query = query.filter(TradeRecord.strategy_used == strategy)
    trades = query.order_by(TradeRecord.close_time.desc()).limit(limit).all()

    return [
        TradeResponse(
            id=t.id,
            ticket=t.ticket,
            symbol=t.symbol,
            trade_type=t.trade_type,
            volume=t.volume,
            open_price=t.open_price,
            close_price=t.close_price,
            sl=t.sl,
            tp=t.tp,
            open_time=t.open_time,
            close_time=t.close_time,
            gross_pnl=t.gross_pnl,
            net_pnl=t.net_pnl,
            commission=t.commission,
            swap=t.swap,
            slippage=t.slippage,
            exit_reason=t.exit_reason,
            strategy_used=t.strategy_used,
            model_version=t.model_version,
            market_regime=t.market_regime
        )
        for t in trades
    ]
