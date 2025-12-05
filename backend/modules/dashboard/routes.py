"""
Dashboard API routes.

This module defines FastAPI routes for the dashboard, including project
management, run monitoring, configuration, and test simulation endpoints.
"""

import hmac
import hashlib
import time
from typing import List, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_session
from schemas.dashboard import (
    ProjectCreateSchema,
    ProjectUpdateSchema,
    ProjectResponseSchema,
    RunResponseSchema,
    ApiKeyConfigSchema,
    TestSlackCommandSchema,
    TestSlackResponseSchema
)
from modules.dashboard.service import get_dashboard_service, DashboardService
from utils.logging import get_logger

logger = get_logger("dashboard.routes")

# Create router
router = APIRouter()


# ============================================================================
# PROJECT MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/projects", response_model=List[ProjectResponseSchema])
async def list_projects(
    session: AsyncSession = Depends(get_session),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get all project mappings.
    
    Returns list of projects with channel→repository configurations.
    """
    try:
        projects = await service.get_projects(session)
        return [ProjectResponseSchema.model_validate(p) for p in projects]
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve projects"
        )


@router.post("/projects", response_model=ProjectResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreateSchema,
    session: AsyncSession = Depends(get_session),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Create a new project mapping.
    
    Links a Slack channel to a Git repository.
    """
    try:
        project = await service.create_project(data, session)
        return ProjectResponseSchema.model_validate(project)
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project"
        )


@router.put("/projects/{project_id}", response_model=ProjectResponseSchema)
async def update_project(
    project_id: str,
    data: ProjectUpdateSchema,
    session: AsyncSession = Depends(get_session),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Update an existing project mapping.
    
    Can update repository URL or default branch.
    """
    try:
        project = await service.update_project(project_id, data, session)
        return ProjectResponseSchema.model_validate(project)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project"
        )


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Delete a project mapping.
    
    Note: This will also delete all associated runs (cascade).
    """
    try:
        success = await service.delete_project(project_id, session)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project"
        )


# ============================================================================
# RUN MONITORING ENDPOINTS
# ============================================================================

@router.get("/runs", response_model=List[RunResponseSchema])
async def list_runs(
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get run history with optional filters.
    
    Query parameters:
    - status: Filter by status (queued, running, succeeded, failed, cancelled)
    - project_id: Filter by project UUID
    - limit: Maximum number of results (default 50)
    """
    try:
        runs = await service.get_runs(session, status, project_id, limit)
        return [RunResponseSchema.model_validate(r) for r in runs]
    except Exception as e:
        logger.error(f"Failed to list runs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve runs"
        )


@router.get("/runs/{run_id}", response_model=RunResponseSchema)
async def get_run(
    run_id: str,
    session: AsyncSession = Depends(get_session),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get detailed information for a single run.
    
    Includes full execution history and status.
    """
    try:
        run = await service.get_run_details(run_id, session)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Run {run_id} not found"
            )
        return RunResponseSchema.model_validate(run)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get run: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve run"
        )


# ============================================================================
# CONFIGURATION ENDPOINTS
# ============================================================================

@router.get("/config/api-keys", response_model=ApiKeyConfigSchema)
async def get_api_config(
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get current API key configuration.
    
    Returns the provider, model ID, and API key (partially masked).
    """
    try:
        config = service.get_api_config()
        # Mask API key for security (show only last 4 chars)
        if len(config.api_key) > 4:
            config.api_key = "..." + config.api_key[-4:]
        return config
    except Exception as e:
        logger.error(f"Failed to get API config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration"
        )


@router.post("/config/api-keys")
async def update_api_config(
    config: ApiKeyConfigSchema,
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Update API key configuration.
    
    ⚠️ WARNING: Requires backend restart to take effect!
    
    Updates the .env file with new provider credentials.
    """
    try:
        result = service.update_api_config(config)
        return result
    except Exception as e:
        logger.error(f"Failed to update API config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


# ============================================================================
# TEST/SIMULATION ENDPOINTS
# ============================================================================

def generate_slack_signature(timestamp: str, body: str) -> str:
    """
    Generate a valid Slack signature for testing.
    
    This creates signatures that pass Slack's verification, allowing
    the test panel to simulate authentic Slack webhook calls.
    """
    secret = settings.slack_signing_secret
    sig_basestring = f"v0:{timestamp}:{body}"
    signature = hmac.new(
        secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"v0={signature}"


@router.post("/test/slack-command", response_model=TestSlackResponseSchema)
async def test_slack_command(
    request: TestSlackCommandSchema
):
    """
    Simulate a Slack slash command for testing.
    
    This endpoint generates a valid Slack webhook request and sends it
    to the actual /slack/events endpoint, allowing you to test the full
    integration without using real Slack.
    
    The request includes proper Slack signatures for authentication.
    """
    try:
        # Prepare form data like Slack would send
        form_data = {
            "token": "test_verification_token",
            "team_id": request.team_id,
            "team_domain": request.team_domain,
            "channel_id": request.channel_id,
            "channel_name": "test-channel",
            "user_id": request.user_id,
            "user_name": request.user_name,
            "command": request.command,
            "text": request.text,
            "response_url": "https://hooks.slack.com/commands/test",
            "trigger_id": "test_trigger_id"
        }
        
        # Generate request body as Slack would encode it
        body = urlencode(form_data)
        timestamp = str(int(time.time()))
        
        # Generate valid Slack signature
        signature = generate_slack_signature(timestamp, body)
        
        logger.info(f"Test command simulation: {request.command} {request.text}")
        
        # Import here to avoid circular dependency
        from fastapi.testclient import TestClient
        from main import app
        
        # Make internal request to /slack/events
        client = TestClient(app)
        response = client.post(
            "/slack/events",
            data=form_data,
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature,
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        
        # Parse response
        response_data = response.json() if response.status_code == 200 else None
        
        return TestSlackResponseSchema(
            success=response.status_code == 200,
            message=f"Command {'executed' if response.status_code == 200 else 'failed'}",
            run_id=None,  # Could parse from response if needed
            request_payload=form_data,
            response_payload=response_data
        )
        
    except Exception as e:
        logger.error(f"Test command failed: {e}")
        return TestSlackResponseSchema(
            success=False,
            message=f"Test failed: {str(e)}",
            run_id=None,
            request_payload=None,
            response_payload=None
        )


@router.get("/health")
async def dashboard_health():
    """Health check for dashboard API."""
    return {
        "status": "healthy",
        "module": "dashboard"
    }
