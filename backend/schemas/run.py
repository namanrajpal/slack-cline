"""
Pydantic schemas for run-related API operations.

This module contains schemas for run creation, updates, and responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from models.run import RunStatus


class CreateRunRequest(BaseModel):
    """
    Request schema for creating a new run.
    
    This is used for API endpoints that create runs programmatically
    (though most runs will be created via Slack commands).
    """
    
    project_id: UUID = Field(..., description="Project (channel-repo mapping) ID")
    task_prompt: str = Field(..., description="Task description", min_length=1, max_length=5000)
    slack_channel_id: Optional[str] = Field(None, description="Slack channel ID if triggered from Slack")


class RunResponseSchema(BaseModel):
    """
    Response schema for run data.
    
    This is used when returning run information via API endpoints
    or for serializing run data in responses.
    """
    
    id: UUID = Field(..., description="Run ID")
    tenant_id: str = Field(..., description="Tenant ID")
    project_id: UUID = Field(..., description="Project ID")
    cline_run_id: Optional[str] = Field(None, description="Cline Core run ID")
    status: RunStatus = Field(..., description="Current run status")
    task_prompt: str = Field(..., description="Task description")
    slack_channel_id: Optional[str] = Field(None, description="Slack channel ID")
    slack_thread_ts: Optional[str] = Field(None, description="Slack thread timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    finished_at: Optional[datetime] = Field(None, description="Completion timestamp")
    summary: Optional[str] = Field(None, description="Execution summary")
    
    class Config:
        from_attributes = True  # Enable ORM mode for SQLAlchemy models


class RunEventSchema(BaseModel):
    """
    Schema for run events from Cline Core.
    
    This represents events that come from Cline Core during execution
    and need to be processed by the orchestrator.
    """
    
    run_id: str = Field(..., description="Run ID (from our system)")
    cline_run_id: str = Field(..., description="Cline Core run ID")
    event_type: str = Field(..., description="Type of event")
    timestamp: datetime = Field(..., description="Event timestamp")
    data: dict = Field(default_factory=dict, description="Event-specific data")
    message: Optional[str] = Field(None, description="Human-readable message")


class RunListResponse(BaseModel):
    """
    Response schema for listing runs with pagination.
    """
    
    runs: list[RunResponseSchema] = Field(..., description="List of runs")
    total: int = Field(..., description="Total number of runs")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of runs per page")


class RunStatsResponse(BaseModel):
    """
    Response schema for run statistics.
    """
    
    total_runs: int = Field(..., description="Total number of runs")
    active_runs: int = Field(..., description="Number of active runs")
    successful_runs: int = Field(..., description="Number of successful runs")
    failed_runs: int = Field(..., description="Number of failed runs")
    cancelled_runs: int = Field(..., description="Number of cancelled runs")
