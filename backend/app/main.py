"""
TradePilot AI - FastAPI Application Entrypoint
Autonomous Forex Trading and Analytics Platform (DEMO-ONLY)
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import settings
from backend.app.core.database import init_db
from backend.app.core.events import logger
from backend.app.services.scheduler import engine_scheduler

from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.mt5 import router as mt5_router
from backend.app.api.v1.market import router as market_router
from backend.app.api.v1.analysis import router as analysis_router
from backend.app.api.v1.bot import router as bot_router
from backend.app.api.v1.positions import router as positions_router
from backend.app.api.v1.risk import router as risk_router
from backend.app.api.v1.backtest import router as backtest_router
from backend.app.api.v1.reports import router as reports_router
from backend.app.api.v1.settings import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Initializing TradePilot AI backend engine...")
    init_db()
    logger.info("Database schema initialized.")

    # Start background scheduler worker
    engine_scheduler.start_worker()

    yield

    # Clean shutdown
    logger.info("Shutting down TradePilot AI background worker...")
    engine_scheduler.stop_worker()
    logger.info("TradePilot AI backend shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Heavy Autonomous Forex Trading and Analytics Platform (Strictly DEMO-ONLY Mode)",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global safety exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled error at {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal engine error occurred. Check audit logs for details."}
    )

# Include all API v1 routers with /api prefix
api_prefix = "/api"
app.include_router(health_router, prefix=api_prefix)
app.include_router(mt5_router, prefix=api_prefix)
app.include_router(market_router, prefix=api_prefix)
app.include_router(analysis_router, prefix=api_prefix)
app.include_router(bot_router, prefix=api_prefix)
app.include_router(positions_router, prefix=api_prefix)
app.include_router(risk_router, prefix=api_prefix)
app.include_router(backtest_router, prefix=api_prefix)
app.include_router(reports_router, prefix=api_prefix)
app.include_router(settings_router, prefix=api_prefix)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False
    )
