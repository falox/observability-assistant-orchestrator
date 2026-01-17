"""FastAPI application entry point.

This module initializes the FastAPI application with:
- CORS middleware for cross-origin requests
- AG-UI chat router for agent communication
- Health check endpoints for container orchestration
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agui.router import router as agui_router
from .config.settings import Settings
from .utils.logging import setup_logging

logger = logging.getLogger(__name__)

# Module-level settings instance for version info
_settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler.

    Configures logging on startup and logs shutdown message on teardown.

    Args:
        app: The FastAPI application instance.

    Yields:
        None after startup, resumes on shutdown.
    """
    settings = Settings()
    setup_logging(settings.log_level)
    logger.info("Orchestrator starting up...")
    logger.info("Observability Agent URL: %s", settings.observability_agent_url)
    logger.info("Generic Agent URL: %s", settings.generic_agent_url)
    yield
    logger.info("Orchestrator shutting down...")


app = FastAPI(
    title="Observability Assistant Orchestrator",
    description="Dispatches observability and troubleshooting tasks to A2A agents",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware - permissive for development, should be restricted in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agui_router)


@app.get("/health/live")
async def liveness() -> dict[str, str]:
    """Liveness probe endpoint.

    Returns:
        Status indicating the service is running.
    """
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness() -> dict[str, str]:
    """Readiness probe endpoint.

    Returns:
        Status indicating the service is ready to accept requests.
    """
    # Future: Could check A2A agent connectivity here
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, object]:
    """Root endpoint with API info.

    Returns:
        API metadata including name, version, and available endpoints.
    """
    return {
        "name": "Observability Assistant Orchestrator",
        "version": "0.1.0",
        "endpoints": {
            "agui_chat": "/api/agui/chat",
            "health_live": "/health/live",
            "health_ready": "/health/ready",
        },
    }


def main() -> None:
    """Run the application using uvicorn."""
    settings = Settings()
    uvicorn.run(
        "orchestrator.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=False,
    )


if __name__ == "__main__":
    main()
