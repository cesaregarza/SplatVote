"""FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vote_api.connections import async_engine, db_context
from vote_api.middleware import RateLimitMiddleware
from vote_api.routes import (
    admin_router,
    auth_router,
    categories_router,
    health_router,
    results_router,
    votes_router,
)
from vote_api.services.category_sync import CategorySyncService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting SplatVote API...")

    # Sync categories on startup if enabled. In dev mode, default to enabled
    # unless explicitly disabled via SYNC_ON_STARTUP=false.
    sync_on_startup_raw = os.getenv("SYNC_ON_STARTUP")
    if sync_on_startup_raw is None:
        sync_on_startup = os.getenv("DEV_MODE", "false").lower() == "true"
    else:
        sync_on_startup = sync_on_startup_raw.lower() == "true"

    logger.info("Category sync on startup enabled: %s", sync_on_startup)

    if sync_on_startup:
        try:
            async with db_context() as session:
                sync_service = CategorySyncService(session)
                results = await sync_service.sync_all()
                logger.info(f"Category sync completed: {results}")
        except Exception:
            logger.exception("Category sync failed on startup")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down SplatVote API...")
    await async_engine.dispose()


# Create application
app = FastAPI(
    title="SplatVote API",
    description="Community voting platform for Splatoon 3",
    version="1.0.0",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(RateLimitMiddleware)

# Setup CORS
allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(votes_router)
app.include_router(results_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "SplatVote API",
        "version": "1.0.0",
        "docs": "/docs",
    }


# Run the app using Uvicorn programmatically
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
