"""
Chat schemas for conversation listing and thread management.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ConversationSummary(BaseModel):
    """Summary of a conversation for listing."""
    
    model_config = ConfigDict(from_attributes=True)
    
    thread_id: str
    channel_id: str
    project_id: Optional[UUID] = None
    updated_at: datetime
    message_count: int
    
    # Derived from state_json
    title: str  # First user message or fallback
    last_message_preview: str


class ConversationListResponse(BaseModel):
    """Response for listing conversations."""
    
    conversations: list[ConversationSummary]
