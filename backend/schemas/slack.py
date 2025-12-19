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
    a slash command like `/sline help` or `/sline <prompt>`.
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
    
    Note: action_ts is only present in message actions, not block actions (button clicks).
    """
    
    type: str = Field(..., description="Type of interaction")
    token: str = Field(..., description="Slack verification token")
    action_ts: Optional[str] = Field(None, description="Timestamp of the action (message actions only)")
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
