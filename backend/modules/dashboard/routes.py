"""
Dashboard API routes.

This module defines FastAPI routes for the dashboard, including project
management, run monitoring, configuration, and test simulation endpoints.
"""

import asyncio
import hmac
import hashlib
import json
import time
from typing import List, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
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
    TestSlackResponseSchema,
    RunRespondSchema,
    RunRespondResponseSchema,
    McpServerCreateSchema,
    McpServerUpdateSchema,
    McpServerResponseSchema
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


@router.post("/runs/{run_id}/respond", response_model=RunRespondResponseSchema)
async def respond_to_run(
    run_id: str,
    request: RunRespondSchema,
    session: AsyncSession = Depends(get_session),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Send an approval or denial response to a running Cline task.
    
    Use this when Cline is waiting for user approval to execute a command
    or perform an action. Only valid for runs in 'running' status.
    
    Actions:
    - approve: Allow Cline to proceed with the proposed action
    - deny: Reject the proposed action
    """
    try:
        # Get run details to find the instance
        run = await service.get_run_details(run_id, session)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Run {run_id} not found"
            )
        
        # Validate run is still running
        if run.status.value not in ('RUNNING',):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot respond to run with status: {run.status.value}"
            )
        
        # Get instance info from orchestrator
        from modules.orchestrator.service import get_orchestrator_service
        orchestrator = get_orchestrator_service()
        metadata = orchestrator._run_metadata.get(run_id)
        
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Run metadata not found - task may have completed"
            )
        
        # Validate action
        if request.action not in ('approve', 'deny'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {request.action}. Must be 'approve' or 'deny'"
            )
        
        # Send response via CLI client
        from modules.execution_engine.cli_client import get_cli_client
        cli_client = get_cli_client()
        
        success = await cli_client.send_response(
            instance_address=metadata["instance_address"],
            workspace_path=metadata["workspace_path"],
            action=request.action,
            message=request.message
        )
        
        if success:
            logger.info(f"Sent {request.action} response to run {run_id}")
            return RunRespondResponseSchema(
                success=True,
                message=f"Response '{request.action}' sent successfully",
                action=request.action,
                run_id=run_id
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send response to Cline"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to respond to run {run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send response: {str(e)}"
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

@router.post("/test/slack-command", response_model=TestSlackResponseSchema)
async def test_slack_command(
    request: TestSlackCommandSchema
):
    """
    Simulate a Slack slash command for testing.
    
    This endpoint calls the Slack handler directly, allowing you to test
    the full integration without using real Slack.
    """
    try:
        logger.info(f"Test command simulation: {request.command} {request.text}")
        
        # Import Slack schemas and handler
        from fastapi import BackgroundTasks
        from schemas.slack import SlackCommandSchema
        from modules.slack_gateway.handlers import handle_cline_command
        
        # Create Slack command schema (mimics real Slack payload)
        command_data = SlackCommandSchema(
            token="test_verification_token",
            team_id=request.team_id,
            team_domain=request.team_domain,
            channel_id=request.channel_id,
            channel_name="test-channel",
            user_id=request.user_id,
            user_name=request.user_name,
            command=request.command,
            text=request.text,
            response_url="https://hooks.slack.com/commands/test",
            trigger_id="test_trigger_id"
        )
        
        # Create BackgroundTasks instance for the handler
        background_tasks = BackgroundTasks()
        
        # Call the Slack handler directly (same execution path as real Slack)
        response = await handle_cline_command(command_data, background_tasks)
        
        # Extract response data
        response_body = None
        if hasattr(response, 'body'):
            import json
            response_body = json.loads(response.body.decode('utf-8'))
        
        return TestSlackResponseSchema(
            success=True,
            message="Command executed successfully",
            run_id=None,  # Could extract from response if needed
            request_payload=command_data.dict(),
            response_payload=response_body
        )
        
    except Exception as e:
        logger.error(f"Test command failed: {e}", exc_info=True)
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


# ============================================================================
# SLINE AGENT TEST ENDPOINTS
# ============================================================================

@router.post("/test/sline-chat")
async def test_sline_chat(
    request: TestSlackCommandSchema,
    session: AsyncSession = Depends(get_session)
):
    """
    Test the Sline agent directly without Slack integration.
    
    This calls the AgentService directly to test the LangGraph-based agent.
    """
    try:
        logger.info(f"Sline chat test: {request.text}")
        
        from modules.agent.service import get_agent_service
        
        agent_service = get_agent_service()
        
        # Use the text as the message, channel_id for project lookup
        response = await agent_service.handle_message(
            channel_id=request.channel_id,
            thread_ts="test-thread-123",  # Use trigger_id as thread_ts for testing
            user_id=request.user_id,
            text=request.text,
            session=session,
        )
        
        return {
            "success": True,
            "message": "Sline responded",
            "response": response,
            "channel_id": request.channel_id,
            "thread_ts": "test-thread-123",
        }
        
    except Exception as e:
        logger.error(f"Sline chat test failed: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Test failed: {str(e)}",
            "response": None,
        }


# ============================================================================
# REAL-TIME EVENT STREAMING (SSE)
# ============================================================================

@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: str,
    session: AsyncSession = Depends(get_session),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Stream real-time events for a run using Server-Sent Events (SSE).
    
    Connect to this endpoint to receive live updates as the run executes.
    Events are sent in the format: data: {"event_type": "...", "message": "..."}
    """
    # Verify run exists
    run = await service.get_run_details(run_id, session)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )
    
    async def event_generator():
        """Generate SSE events for the run."""
        from modules.orchestrator.service import get_orchestrator_service
        
        orchestrator = get_orchestrator_service()
        
        # Send initial status
        yield f"data: {json.dumps({'event_type': 'connected', 'message': f'Connected to run {run_id}', 'run_id': run_id})}\n\n"
        
        # Check if run is already complete
        if run.status.value in ('SUCCEEDED', 'FAILED', 'CANCELLED'):
            yield f"data: {json.dumps({'event_type': 'complete', 'message': f'Run already completed with status: {run.status.value}', 'status': run.status.value})}\n\n"
            return
        
        # Send current status
        yield f"data: {json.dumps({'event_type': 'status', 'message': f'Current status: {run.status.value}', 'status': run.status.value})}\n\n"
        
        # Subscribe to events for this run
        # We'll poll the orchestrator's event queue or use the CLI output directly
        metadata = orchestrator._run_metadata.get(run_id)
        
        if not metadata:
            yield f"data: {json.dumps({'event_type': 'info', 'message': 'Run metadata not found - run may have already completed'})}\n\n"
            # Still poll for completion
            for _ in range(60):  # Poll for up to 60 seconds
                await asyncio.sleep(1)
                async for sess in get_session():
                    updated_run = await service.get_run_details(run_id, sess)
                    if updated_run and updated_run.status.value in ('SUCCEEDED', 'FAILED', 'CANCELLED'):
                        yield f"data: {json.dumps({'event_type': 'complete', 'message': updated_run.summary or 'Run completed', 'status': updated_run.status.value})}\n\n"
                        return
            return
        
        # Stream events from CLI output
        from modules.execution_engine.cli_client import get_cli_client
        cli_client = get_cli_client()
        
        try:
            async for event in cli_client.stream_events(
                metadata["instance_address"],
                metadata["workspace_path"],
                metadata["task_id"]
            ):
                event_data = {
                    "event_type": event.event_type,
                    "message": event.message,
                    "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                    "data": event.data
                }
                yield f"data: {json.dumps(event_data)}\n\n"
                
                # Exit if run is complete
                if event.event_type in ("complete", "error", "failed"):
                    break
                    
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for run {run_id}")
        except Exception as e:
            logger.error(f"Error streaming events for run {run_id}: {e}")
            yield f"data: {json.dumps({'event_type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# ============================================================================
# MCP SERVER ENDPOINTS
# ============================================================================

@router.get("/mcp-servers", response_model=List[McpServerResponseSchema])
async def list_mcp_servers(
    session: AsyncSession = Depends(get_session),
    service: DashboardService = Depends(get_dashboard_service)
):
    """Get all MCP servers."""
    try:
        servers = await service.get_mcp_servers(session)
        return [McpServerResponseSchema.model_validate(s) for s in servers]
    except Exception as e:
        logger.error(f"Failed to list MCP servers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve MCP servers"
        )


@router.post("/mcp-servers", response_model=McpServerResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_mcp_server(
    data: McpServerCreateSchema,
    session: AsyncSession = Depends(get_session),
    service: DashboardService = Depends(get_dashboard_service)
):
    """Create a new MCP server."""
    try:
        server = await service.create_mcp_server(data, session)
        return McpServerResponseSchema.model_validate(server)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create MCP server: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create MCP server"
        )


@router.put("/mcp-servers/{server_id}", response_model=McpServerResponseSchema)
async def update_mcp_server(
    server_id: str,
    data: McpServerUpdateSchema,
    session: AsyncSession = Depends(get_session),
    service: DashboardService = Depends(get_dashboard_service)
):
    """Update an existing MCP server."""
    try:
        server = await service.update_mcp_server(server_id, data, session)
        return McpServerResponseSchema.model_validate(server)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update MCP server: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update MCP server"
        )


@router.delete("/mcp-servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server(
    server_id: str,
    session: AsyncSession = Depends(get_session),
    service: DashboardService = Depends(get_dashboard_service)
):
    """Delete an MCP server."""
    try:
        success = await service.delete_mcp_server(server_id, session)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP server {server_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete MCP server: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete MCP server"
        )
