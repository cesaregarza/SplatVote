"""Health check endpoints."""

from fastapi import APIRouter

from vote_api.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for Kubernetes probes."""
    return HealthResponse(status="healthy", version="1.0.0")


@router.get("/ready", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    """Readiness check endpoint for Kubernetes probes."""
    # Could add DB/Redis connectivity checks here
    return HealthResponse(status="ready", version="1.0.0")
