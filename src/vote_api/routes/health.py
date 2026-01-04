"""Health check endpoints."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from vote_api.connections import async_session_factory, get_redis
from vote_api.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for Kubernetes probes."""
    return HealthResponse(status="healthy", version="1.0.0")


@router.get("/ready", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    """Readiness check endpoint for Kubernetes probes."""
    errors = []

    # Check database connectivity
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        errors.append(f"Database: {str(e)}")

    # Check Redis connectivity
    try:
        redis_client = get_redis()
        redis_client.ping()
    except Exception as e:
        errors.append(f"Redis: {str(e)}")

    if errors:
        raise HTTPException(status_code=503, detail="; ".join(errors))

    return HealthResponse(status="ready", version="1.0.0")
