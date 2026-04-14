"""
api/health.py

/health endpoint — required by load balancers, Docker, and ECS health checks.
Returns 200 if app is up; 503 if DB is unreachable.
No auth required.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.core.database import check_db_health

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    """
    Lightweight health endpoint.
    Checks DB connectivity; Redis check added in Phase 2.
    """
    db_ok = await check_db_health()

    if db_ok:
        return JSONResponse(
            status_code=200,
            content={"status": "healthy", "db": "ok"},
        )
    else:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "db": "unreachable"},
        )
