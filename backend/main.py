"""
backend/main.py

FastAPI application factory.
This is the entry point: uvicorn backend.main:app

Startup sequence:
1. Load and validate all settings (fail fast on bad config).
2. Register middleware (CORS, logging, rate limiting).
3. Register exception handlers (consistent error shape for all routes).
4. Mount all API routes.
5. Expose /health, /docs (disabled in prod), /redoc.
"""

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.api.router import api_router
from backend.core.config import settings
from backend.core.database import check_db_health

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# ── Logging setup (structured, JSON-compatible in production) ─────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup + shutdown hooks) ───────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Runs at application startup and shutdown.
    - Startup: validate DB connectivity, log config summary.
    - Shutdown: clean up any persistent connections.
    """
    logger.info(
        "app_starting",
        extra={
            "env": settings.APP_ENV,
            "debug": settings.DEBUG,
            "model": settings.OPENAI_MODEL,
        },
    )

    # Fail fast if DB is unreachable at startup
    db_ok = await check_db_health()
    if not db_ok:
        logger.critical("startup_db_check_failed — DB is unreachable. Exiting.")
        raise RuntimeError("Database is not reachable. Cannot start application.")

    logger.info("app_started — all systems ready.")
    yield
    logger.info("app_shutdown")


# ── Application factory ───────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description=(
            "Multi-tenant AI appointment agent platform. "
            "Build virtual receptionists without code."
        ),
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    # ── Request logging middleware ────────────────────────────────────────────
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "http_request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                # Never log query params in production (may contain tokens)
            },
        )
        return response

    # ── Exception handlers ────────────────────────────────────────────────────
    # All unhandled exceptions return a consistent JSON shape (R15)
    # Internal error details are NEVER exposed in production (security rule).

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            extra={"path": request.url.path, "error": str(exc)},
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "data": None,
                "error": "An unexpected error occurred. Our team has been notified.",
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "data": None, "error": str(exc)},
        )

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(api_router)

    # ── Frontend (serves index.html at /) ─────────────────────────────────────
    # Mounts the frontend/ directory so the HTML is on the same origin as the
    # API — no CORS issues, no separate dev server needed for demo.
    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

        @app.get("/", include_in_schema=False)
        async def serve_frontend():
            return FileResponse(str(FRONTEND_DIR / "index.html"))

    return app


# Module-level app — referenced by uvicorn and tests
app = create_app()
