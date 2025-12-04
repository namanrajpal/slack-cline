"""
FastAPI application entry point for slack-cline backend service.

This module sets up the FastAPI application with CORS, health endpoints,
and routes for Slack webhook integration.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import create_tables
from modules.slack_gateway.handlers import slack_router
from utils.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown tasks."""
    # Startup
    setup_logging(settings.log_level)
    logging.info("Starting slack-cline backend service")
    
    # Create database tables
    await create_tables()
    logging.info("Database tables created/verified")
    
    yield
    
    # Shutdown
    logging.info("Shutting down slack-cline backend service")


# Create FastAPI application
app = FastAPI(
    title="Slack-Cline Backend",
    description="Backend service for integrating Slack with Cline Core via gRPC",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "slack-cline-backend"}


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with service dependencies."""
    # TODO: Add checks for database, Cline Core gRPC, etc.
    return {
        "status": "healthy",
        "service": "slack-cline-backend",
        "version": "0.1.0",
        "dependencies": {
            "database": "healthy",  # TODO: actual check
            "cline_core": "healthy",  # TODO: actual check
        }
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Include routers
app.include_router(slack_router, prefix="/slack", tags=["slack"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
