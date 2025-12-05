"""
Pydantic schemas for Dashboard API.

This module contains schemas for validating dashboard API requests
and responses, including project management, run queries, and configuration.
"""

from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class ProjectCreateSchema(BaseModel):
    """Schema for creating a new project mapping."""
    
    tenant_id: str = Field(default="default", description="Tenant identifier")
    slack_channel_id: str = Field(..., description="Slack channel ID")
    repo_url: str = Field(..., description="Git repository URL")
    default_ref: str = Field(default="main", description="Default branch/ref")


class ProjectUpdateSchema(BaseModel):
    """Schema for updating an existing project."""
    
    repo_url: Optional[str] = Field(None, description="Git repository URL")
    default_ref: Optional[str] = Field(None, description="Default branch/ref")


class ProjectResponseSchema(BaseModel):
    """Schema for project response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: str
    slack_channel_id: str
    repo_url: str
    default_ref: str
    created_at: datetime
    updated_at: datetime


class RunResponseSchema(BaseModel):
    """Schema for run response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    project_id: UUID
    tenant_id: str
    status: str
    task_prompt: str
    slack_channel_id: str
    cline_run_id: Optional[str]
    cline_instance_address: Optional[str]
    workspace_path: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    summary: Optional[str]


class ApiKeyConfigSchema(BaseModel):
    """Schema for API key configuration."""
    
    provider: str = Field(..., description="LLM provider ID")
    api_key: str = Field(..., description="API key for the provider")
    model_id: str = Field(..., description="Model ID to use")
    base_url: Optional[str] = Field(None, description="Base URL for OpenAI-compatible providers")


class TestSlackCommandSchema(BaseModel):
    """Schema for simulating Slack slash commands in test panel."""
    
    channel_id: str = Field(..., description="Slack channel ID")
    user_id: str = Field(default="U_TEST_USER", description="Test user ID")
    user_name: str = Field(default="test_user", description="Test username")
    command: str = Field(default="/cline", description="Slash command")
    text: str = Field(..., description="Command text (e.g., 'run create a readme')")
    team_id: str = Field(default="T_TEST_TEAM", description="Test team ID")
    team_domain: str = Field(default="test-workspace", description="Test team domain")


class TestSlackResponseSchema(BaseModel):
    """Schema for test simulation response."""
    
    success: bool
    message: str
    run_id: Optional[str] = None
    request_payload: Optional[dict] = None
    response_payload: Optional[dict] = None
