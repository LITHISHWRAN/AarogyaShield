from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging
from app.api.v1.router import api_router
from app.db.session import init_db
from typing import List

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await init_db()
    logger.info("AarogyaShield backend started", env=settings.APP_ENV)
    yield
    logger.info("AarogyaShield backend shutting down")


app = FastAPI(
    title="AarogyaShield API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.BACKEND_CORS_ORIGINS.split(",")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def readiness():
    from app.db.session import check_db
    from app.services.session_service import check_redis
    from app.services.vector_service import check_qdrant

    checks = {
        "postgres": await check_db(),
        "redis": await check_redis(),
        "qdrant": await check_qdrant(),
    }
    healthy = all(checks.values())
    return {"status": "ready" if healthy else "degraded", "checks": checks}
