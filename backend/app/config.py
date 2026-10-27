"""
TradePilot AI - Application Configuration & Safeguards
"""
import os
import json
from typing import List, Dict, Any, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "TradePilot AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    # DEMO-ONLY SAFETY ENFORCEMENT
    # Live trading must be technically blocked in this version
    TRADING_MODE: str = Field(default="demo", description="Trading mode: strictly 'demo'")
    LIVE_TRADING_ENABLED: bool = Field(default=False, description="Live trading flag: strictly False")

    ALLOWED_SYMBOLS: Any = Field(default=["EURUSD"])
    DEFAULT_SYMBOL: str = "EURUSD"
    DEFAULT_TIMEFRAME: str = "M15"
    HTF_TIMEFRAME: str = "H1"

    # MetaTrader 5 Configuration
    MT5_PATH: str = ""
    MT5_LOGIN: Optional[int] = None
    MT5_PASSWORD: str = ""
    MT5_SERVER: str = ""
    MT5_TIMEOUT_MS: int = 60000
    MT5_PORTABLE: bool = False
    MT5_USE_MOCK_FALLBACK: bool = True
    MT5_SYMBOL_MAP: Any = Field(default={"EURUSD": "EURUSD"})

    # Deterministic Risk Management Safeguards
    MAX_RISK_PER_TRADE_PCT: float = Field(default=0.25, ge=0.01, le=1.0)
    MAX_TOTAL_OPEN_RISK_PCT: float = Field(default=0.50, ge=0.05, le=2.0)
    MAX_DAILY_LOSS_PCT: float = Field(default=1.0, ge=0.1, le=5.0)
    MAX_WEEKLY_LOSS_PCT: float = Field(default=3.0, ge=0.5, le=10.0)
    MAX_CONSECUTIVE_LOSSES: int = Field(default=3, ge=1, le=10)
    MAX_TRADES_PER_DAY: int = Field(default=5, ge=1, le=50)
    MAX_SPREAD_PIPS: float = Field(default=2.5, ge=0.1, le=10.0)
    SLIPPAGE_TOLERANCE_POINTS: int = Field(default=10, ge=1, le=50)

    # AI Provider Settings
    AI_PROVIDER: str = "local_fallback"  # local_fallback, openai, gemini, claude, ollama
    AI_API_KEY: str = ""
    AI_API_BASE: str = ""
    AI_MODEL_NAME: str = "tradepilot-deterministic-v1"
    AI_TIMEOUT_SECONDS: int = 15

    DATABASE_URL: str = "sqlite:///./data/tradepilot.db"
    EVALUATION_INTERVAL_SECONDS: int = 10
    AUTO_RECONCILE_INTERVAL_SECONDS: int = 30
    SECRET_KEY: str = "tradepilot-local-dev-secret-key-32chars"
    AUTH_API_TOKEN: str = ""
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    CORS_ORIGINS: Any = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("TRADING_MODE")
    @classmethod
    def enforce_demo_mode(cls, v: str) -> str:
        if v.lower() != "demo":
            # Hard refusal for safety: live trading is technically blocked
            raise ValueError("TradePilot AI operates strictly in DEMO-ONLY mode. Live trading is prohibited.")
        return "demo"

    @field_validator("LIVE_TRADING_ENABLED")
    @classmethod
    def block_live_trading(cls, v: bool) -> bool:
        if v is True:
            raise ValueError("LIVE_TRADING_ENABLED cannot be True. Live trading is technically blocked in this MVP.")
        return False

    @field_validator("ALLOWED_SYMBOLS", mode="before")
    @classmethod
    def parse_allowed_symbols(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [s.strip().upper() for s in v.split(",") if s.strip()]
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("MT5_LOGIN", mode="before")
    @classmethod
    def parse_mt5_login(cls, v: Any) -> Optional[int]:
        if v == "" or v is None:
            return None
        try:
            return int(v)
        except Exception:
            return None

    @field_validator("MT5_SYMBOL_MAP", mode="before")
    @classmethod
    def parse_symbol_map(cls, v: Any) -> Dict[str, str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {"EURUSD": "EURUSD"}
        return v


settings = Settings()
