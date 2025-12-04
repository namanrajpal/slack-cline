"""
Pydantic schemas for Slack webhook validation.

This module contains schemas for validating incoming Slack webhook payloads
including slash commands and interactive components.
"""

from typing import Optional

from pydantic import BaseModel, Field


class SlackCommandSchema(BaseModel):
    """
    Schema for validating Slack slash command payloads.
    
    This validates the form data sent by Slack when a user issues
    a slash command like `/cline run <task>`.
    """
    
    token: str = Field(..., description="Slack verification token")
    team_id: str = Field(..., description="Slack team (workspace) ID")
    team_domain: str = Field(..., description="Slack team domain")
    channel_id: str = Field(..., description="Channel where command was issued")
    channel_name: str = Field(..., description="Channel name")
    user_id: str = Field(..., description="User who issued the command")
    user_name: str = Field(..., description="Username who issued the command")
    command: str = Field(..., description="The slash command (/cline)")
    text: str = Field(default="", description="Text after the command")
    response_url: str = Field(..., description="URL for delayed responses")
    trigger_id: str = Field(..., description="Trigger ID for interactive components")


class SlackInteractivitySchema(BaseModel):
    """
    Schema for validating Slack interactive component payloads.
    
    This validates the JSON payload sent when users interact with buttons,
    menus, or other interactive elements in Slack messages.
    """
    
    type: str = Field(..., description="Type of interaction")
    token: str = Field(..., description="Slack verification token")
    action_ts: str = Field(..., description="Timestamp of the action")
    team: dict = Field(..., description="Team information")
    user: dict = Field(..., description="User information")
    channel: dict = Field(..., description="Channel information")
    message: Optional[dict] = Field(None, description="Original message")
    response_url: str = Field(..., description="URL for response")
    actions: Optional[list] = Field(None, description="Actions taken")


class SlackResponseSchema(BaseModel):
    """
    Schema for Slack responses that we send back to Slack.
    
    This defines the structure of messages we post back to Slack
    in response to commands or as progress updates.
    """
    
    response_type: Optional[str] = Field(
        default="in_channel", 
        description="Response type: 'in_channel' or 'ephemeral'"
    )
    text: str = Field(..., description="Main message text")
    blocks: Optional[list] = Field(None, description="Block Kit blocks for rich formatting")
    attachments: Optional[list] = Field(None, description="Legacy attachments")
    replace_original: Optional[bool] = Field(False, description="Replace the original message")
    delete_original: Optional[bool] = Field(False, description="Delete the original message")


class StartRunCommand(BaseModel):
    """
    Internal command schema for starting a new run.
    
    This is used internally to pass validated data between
    the Slack Gateway and Run Orchestrator modules.
    """
    
    tenant_id: str = Field(..., description="Tenant identifier")
    channel_id: str = Field(..., description="Slack channel ID")
    user_id: str = Field(..., description="Slack user ID")
    task_prompt: str = Field(..., description="Task description from user")
    response_url: str = Field(..., description="Slack response URL for updates")
    trigger_id: str = Field(..., description="Slack trigger ID")


class CancelRunCommand(BaseModel):
    """
    Internal command schema for canceling a run.
    
    This is used when a user clicks a "Cancel" button or
    issues a cancellation request.
    """
    
    run_id: str = Field(..., description="Run ID to cancel")
    user_id: str = Field(..., description="User requesting cancellation")
    reason: Optional[str] = Field("User requested", description="Cancellation reason")
