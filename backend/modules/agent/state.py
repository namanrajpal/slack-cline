"""
Sline State Definition

Defines the SlineState TypedDict used throughout the LangGraph workflow.
This state is passed between nodes and persisted in the database.
"""

from typing import Optional, Literal, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class SlineState(TypedDict):
    """
    State object passed through the LangGraph workflow.
    
    Initial state for new conversations should set:
    - mode = "chat" (default starting mode)
    - messages = [] (empty list)
    - All context fields from project/Slack
    
    The messages field uses the add_messages reducer, which automatically
    handles appending new messages and deduplication.
    """
    
    # Conversation messages with reducer for appending
    # The add_messages reducer handles merging messages correctly
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Workspace context
    workspace_path: str      # Cloned repo path, e.g., /home/app/workspaces/project-123
    project_id: str          # UUID of project (channel → repo mapping)
    
    # Slack context
    channel_id: str          # Slack channel ID
    thread_ts: str           # Slack thread timestamp (conversation identifier)
    user_id: str             # Slack user ID who initiated
    
    # Workflow state (default: "chat" for new conversations)
    mode: Literal["chat", "planning", "awaiting_approval", "executing", "completed", "error"]
    
    # Plan/execution context
    plan: Optional[str]      # Generated plan text (when in planning/awaiting_approval)
    error: Optional[str]     # Error message if mode is "error"
    
    # Optional metadata (not required on init)
    files_context: Optional[dict[str, str]]  # Cache of recently read files {path: content}


def create_initial_state(
    workspace_path: str,
    project_id: str,
    channel_id: str,
    thread_ts: str,
    user_id: str,
) -> SlineState:
    """
    Create initial state for a new conversation.
    
    Args:
        workspace_path: Path to the cloned repository
        project_id: UUID of the project
        channel_id: Slack channel ID
        thread_ts: Slack thread timestamp
        user_id: Slack user ID who started the conversation
    
    Returns:
        SlineState with default values for a new conversation
    """
    return SlineState(
        messages=[],
        workspace_path=workspace_path,
        project_id=project_id,
        channel_id=channel_id,
        thread_ts=thread_ts,
        user_id=user_id,
        mode="chat",
        plan=None,
        error=None,
        files_context=None,
    )
