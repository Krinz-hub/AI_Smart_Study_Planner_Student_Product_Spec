from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import get_settings
from app.common.database import get_db
from app.common.logging import get_logger

router = APIRouter(tags=["health"])
logger = get_logger("health")
settings = get_settings()


@router.get("/health")
async def liveness_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    checks = {
        "database": "unknown",
        "pgvector": "unknown",
    }
    
    try:
        # Check basic database connectivity
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            checks["database"] = "healthy"
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        checks["database"] = f"unhealthy: {str(e)}"

    try:
        # Check pgvector extension
        vec_result = await db.execute(
            text("SELECT count(*) FROM pg_extension WHERE extname = 'vector'")
        )
        if vec_result.scalar() >= 1:
            checks["pgvector"] = "installed"
        else:
            checks["pgvector"] = "not_installed"
    except Exception as e:
        logger.warning("pgvector_check_failed", error=str(e))
        checks["pgvector"] = f"check_failed: {str(e)}"

    try:
        # Check MongoDB connection
        from app.common.mongo import ping_mongo
        if await ping_mongo():
            checks["mongodb"] = "healthy"
        else:
            checks["mongodb"] = "unhealthy"
    except Exception as e:
        logger.warning("mongodb_check_failed", error=str(e))
        checks["mongodb"] = f"unhealthy: {str(e)}"

    all_healthy = checks["database"] == "healthy" and checks["mongodb"] == "healthy"
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    response_data = {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }

    if not all_healthy:
        raise HTTPException(status_code=status_code, detail=response_data)

    return response_data
