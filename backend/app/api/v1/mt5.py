"""
MetaTrader 5 broker adapter endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from backend.app.services.mt5_adapter import mt5_adapter
from backend.app.core.security import verify_control_access

router = APIRouter(prefix="/mt5", tags=["MetaTrader 5"])


@router.get("/status")
def get_mt5_status():
    """Retrieve MT5 connection and demo verification status"""
    account_info = None
    if mt5_adapter.is_connected:
        try:
            account_info = mt5_adapter.get_account_info()
        except Exception:
            pass

    return {
        "is_connected": mt5_adapter.is_connected,
        "is_mock": mt5_adapter.is_mock,
        "mode": "DEMO ONLY",
        "account": account_info
    }


@router.post("/connect", dependencies=[Depends(verify_control_access)])
def connect_mt5():
    """Trigger MT5 terminal connection"""
    connected, message = mt5_adapter.connect()
    return {
        "success": connected,
        "message": message,
        "is_connected": mt5_adapter.is_connected,
        "is_mock": mt5_adapter.is_mock,
    }


@router.post("/disconnect", dependencies=[Depends(verify_control_access)])
def disconnect_mt5():
    """Disconnect from MT5 terminal"""
    mt5_adapter.disconnect()
    return {
        "success": True,
        "message": "MT5 disconnected"
    }


@router.get("/account")
def get_mt5_account():
    """Fetch live demo account metrics"""
    if not mt5_adapter.is_connected:
        raise HTTPException(status_code=503, detail="MT5 is disconnected")

    try:
        return mt5_adapter.get_account_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
