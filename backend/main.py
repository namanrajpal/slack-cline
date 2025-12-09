"""
FastAPI application entry point for slack-cline backend service.

This module sets up the FastAPI application with CORS, health endpoints,
and routes for Slack webhook integration.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from config import settings
from database import create_tables, get_session
from models.run import RunModel, RunStatus
from modules.slack_gateway.handlers import slack_router
from modules.dashboard.routes import router as dashboard_router
from modules.auth.github_oauth import auth_router
from utils.logging import setup_logging

# Reduce Slack SDK verbosity
logging.getLogger("slack_sdk").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def cleanup_stale_runs():
    """
    Mark any RUNNING runs as CANCELLED on startup.
    
    This handles cases where the server was restarted or crashed while runs were active.
    Since the processes are already dead, we just update the database status.
    """
    async for session in get_session():
        try:
            # Find all runs stuck in RUNNING status
            result = await session.execute(
                select(RunModel).where(RunModel.status == RunStatus.RUNNING)
            )
            stale_runs = result.scalars().all()
            
            if stale_runs:
                logging.info(f"Found {len(stale_runs)} stale runs, marking as CANCELLED")
                
                for run in stale_runs:
                    run.status = RunStatus.CANCELLED
                    run.summary = "Server restarted - run was interrupted"
                    run.completed_at = datetime.utcnow()
                
                await session.commit()
                logging.info(f"Successfully marked {len(stale_runs)} stale runs as CANCELLED")
            else:
                logging.info("No stale runs found")
                
        except Exception as e:
            logging.error(f"Error cleaning up stale runs: {e}", exc_info=True)
        finally:
            break  # Only need one session iteration


async def shutdown_cleanup():
    """
    Kill all running Cline CLI processes and mark runs as CANCELLED on shutdown.
    
    This ensures clean shutdown with no orphaned processes.
    """
    try:
        from modules.orchestrator.service import get_orchestrator_service
        
        orchestrator = get_orchestrator_service()
        active_runs = list(orchestrator._run_metadata.items())
        
        if active_runs:
            logging.info(f"Shutting down {len(active_runs)} active runs")
            
            async for session in get_session():
                try:
                    for run_id, metadata in active_runs:
                        try:
                            # Kill the Cline CLI process if it exists
                            cli_process = metadata.get("cli_process")
                            if cli_process and hasattr(cli_process, "terminate"):
                                logging.info(f"Terminating Cline CLI process for run {run_id}")
                                cli_process.terminate()
                                try:
                                    cli_process.wait(timeout=5)
                                except:
                                    cli_process.kill()  # Force kill if doesn't terminate
                            
                            # Update database status
                            result = await session.execute(
                                select(RunModel).where(RunModel.id == run_id)
                            )
                            run = result.scalar_one_or_none()
                            
                            if run and run.status == RunStatus.RUNNING:
                                run.status = RunStatus.CANCELLED
                                run.summary = "Server shutdown - run cancelled"
                                run.completed_at = datetime.utcnow()
                                logging.info(f"Marked run {run_id} as CANCELLED")
                        
                        except Exception as e:
                            logging.error(f"Error cleaning up run {run_id}: {e}")
                    
                    await session.commit()
                    logging.info("Successfully cleaned up all active runs")
                    
                except Exception as e:
                    logging.error(f"Error in shutdown cleanup session: {e}", exc_info=True)
                finally:
                    break  # Only need one session iteration
        else:
            logging.info("No active runs to clean up")
            
        # Clear orchestrator metadata
        orchestrator._run_metadata.clear()
        
    except Exception as e:
        logging.error(f"Error in shutdown cleanup: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown tasks."""
    # Startup
    setup_logging(settings.log_level)
    logging.info("Starting slack-cline backend service")
    
    # Create database tables
    await create_tables()
    logging.info("Database tables created/verified")
    
    # Clean up any stale runs from previous session
    await cleanup_stale_runs()
    
    yield
    
    # Shutdown
    logging.info("Shutting down slack-cline backend service")
    
    # Kill active processes and mark runs as cancelled
    await shutdown_cleanup()
    
    logging.info("Shutdown complete")


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
    allow_origins=settings.allowed_origins + ["http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
