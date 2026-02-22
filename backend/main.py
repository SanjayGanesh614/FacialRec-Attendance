# app/main.py
# ─────────────────────────────────────────────────────────────
# FastAPI application factory.
# Creates the app, configures middleware, registers routers,
# handles startup/shutdown lifecycle.
# ─────────────────────────────────────────────────────────────

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.base import engine, Base
from app.db.init_db import init_db
from app.db.base import AsyncSessionLocal


# ── Logging setup ──────────────────────────────────────────────────────────────
logger.remove()
logger.add(
    sys.stdout,
    level=settings.LOG_LEVEL if hasattr(settings, "LOG_LEVEL") else "INFO",
    colorize=True,
    format=(
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level:<8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> — {message}"
    ),
)
logger.add(
    "logs/erp.log",
    level="DEBUG",
    rotation="50 MB",
    retention="90 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} — {message}",
)


# ── App lifespan ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Code here runs at startup (before yield) and shutdown (after yield).
    Used for:
      - Creating DB tables (dev only — use Alembic in production)
      - Seeding initial data
      - Warming up connections
    """
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Create all tables — in production, comment this out and use Alembic migrations
    async with engine.begin() as conn:
        # Import all models so they register with Base.metadata
        from app.models import employee, department, attendance, audit  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified/created")

    # Seed super admin on first run
    async with AsyncSessionLocal() as session:
        await init_db(session)

    logger.success("Application ready — API available at /api/v1")

    yield   # ← app runs here

    # Shutdown
    await engine.dispose()
    logger.info("Database connections closed")


# ── App factory ────────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AttendIQ ERP — Face Recognition Attendance System API.\n\n"
            "**Authentication:**\n"
            "- Browser users: POST /api/v1/auth/login → Bearer token\n"
            "- Pi devices: X-Api-Key header\n\n"
            "**Phase 1** covers: Auth, Employees, Departments, Attendance, Devices."
        ),
        docs_url="/docs",           # Swagger UI
        redoc_url="/redoc",         # ReDoc UI
        lifespan=lifespan,
    )

    # ── CORS ───────────────────────────────────────────────────────────────────
    # Allows the React frontend to call the API from a different origin.
    # In production, set CORS_ORIGINS in .env to your actual portal domain.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request logging middleware ─────────────────────────────────────────────
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.debug(f"→ {request.method} {request.url.path}")
        response = await call_next(request)
        logger.debug(f"← {response.status_code} {request.url.path}")
        return response

    # ── Global exception handler ───────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again."},
        )

    # ── Routes ─────────────────────────────────────────────────────────────────
    app.include_router(api_router)

    # Health check — used by load balancers and monitoring
    @app.get("/health", tags=["System"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    return app


# Module-level app instance (used by uvicorn)
app = create_app()


# ── Dev server ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,         # auto-reload on file changes (dev only)
        log_level="debug",
    )
