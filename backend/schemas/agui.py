"""
AG-UI Protocol event types for chat streaming.

IMPORTANT: AG-UI spec uses camelCase in JSON output.
Use Field(alias=...) for camelCase serialization while keeping
Pythonic snake_case in code.

Ref: https://docs.ag-ui.com/concepts/events
"""

from enum import StrEnum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AGUIEventType(StrEnum):
    """AG-UI Protocol event types."""
    # Lifecycle events
    RUN_STARTED = "runStarted"
    RUN_FINISHED = "runFinished"
    RUN_ERROR = "runError"
    
    # Step events (for grouping tool calls / reasoning phases)
    STEP_STARTED = "stepStarted"
    STEP_FINISHED = "stepFinished"
    
    # Message events
    TEXT_MESSAGE_START = "textMessageStart"
    TEXT_MESSAGE_CONTENT = "textMessageContent"
    TEXT_MESSAGE_END = "textMessageEnd"
    
    # Tool events
    TOOL_CALL_START = "toolCallStart"
    TOOL_CALL_ARGS = "toolCallArgs"
    TOOL_CALL_END = "toolCallEnd"
    
    # State events (optional, for shared state)
    STATE_SNAPSHOT = "stateSnapshot"
    STATE_DELTA = "stateDelta"


class AGUIEvent(BaseModel):
    """Base AG-UI event structure with camelCase JSON output."""
    model_config = ConfigDict(populate_by_name=True)
    
    type: AGUIEventType
    timestamp: Optional[str] = None
    
    def to_sse(self) -> str:
        """Encode as SSE data frame."""
        json_str = self.model_dump_json(by_alias=True, exclude_none=True)
        return f"data: {json_str}\n\n"


class RunStartedEvent(AGUIEvent):
    """Agent run started."""
    type: AGUIEventType = AGUIEventType.RUN_STARTED
    thread_id: str = Field(alias="threadId")
    run_id: str = Field(alias="runId")


class RunFinishedEvent(AGUIEvent):
    """Agent run completed successfully."""
    type: AGUIEventType = AGUIEventType.RUN_FINISHED
    thread_id: str = Field(alias="threadId")
    run_id: str = Field(alias="runId")


class RunErrorEvent(AGUIEvent):
    """Agent run failed."""
    type: AGUIEventType = AGUIEventType.RUN_ERROR
    thread_id: str = Field(alias="threadId")
    run_id: str = Field(alias="runId")
    error: str


class StepStartedEvent(AGUIEvent):
    """Step started (groups tool calls / reasoning phases)."""
    type: AGUIEventType = AGUIEventType.STEP_STARTED
    step_id: str = Field(alias="stepId")
    step_name: Optional[str] = Field(default=None, alias="stepName")


class StepFinishedEvent(AGUIEvent):
    """Step completed."""
    type: AGUIEventType = AGUIEventType.STEP_FINISHED
    step_id: str = Field(alias="stepId")


class TextMessageStartEvent(AGUIEvent):
    """Start of a text message."""
    type: AGUIEventType = AGUIEventType.TEXT_MESSAGE_START
    message_id: str = Field(alias="messageId")
    role: str = "assistant"


class TextMessageContentEvent(AGUIEvent):
    """Streaming text content event."""
    type: AGUIEventType = AGUIEventType.TEXT_MESSAGE_CONTENT
    message_id: str = Field(alias="messageId")
    delta: str  # Incremental text chunk


class TextMessageEndEvent(AGUIEvent):
    """End of a text message."""
    type: AGUIEventType = AGUIEventType.TEXT_MESSAGE_END
    message_id: str = Field(alias="messageId")


class ToolCallStartEvent(AGUIEvent):
    """Tool call initiated."""
    type: AGUIEventType = AGUIEventType.TOOL_CALL_START
    tool_call_id: str = Field(alias="toolCallId")
    tool_name: str = Field(alias="toolName")
    parent_message_id: Optional[str] = Field(default=None, alias="parentMessageId")


class ToolCallArgsEvent(AGUIEvent):
    """Tool call arguments (can be streamed)."""
    type: AGUIEventType = AGUIEventType.TOOL_CALL_ARGS
    tool_call_id: str = Field(alias="toolCallId")
    delta: str  # JSON string chunk


class ToolCallEndEvent(AGUIEvent):
    """Tool call completed."""
    type: AGUIEventType = AGUIEventType.TOOL_CALL_END
    tool_call_id: str = Field(alias="toolCallId")
    result: Optional[str] = None


class ChatMessage(BaseModel):
    """Chat message format for thread reload."""
    model_config = ConfigDict(populate_by_name=True)
    
    id: str
    role: str  # "user" | "assistant"
    content: str
    created_at: Optional[str] = Field(default=None, alias="createdAt")


class ChatRequest(BaseModel):
    """Chat request structure (method-based routing)."""
    model_config = ConfigDict(populate_by_name=True)
    
    method: Optional[str] = None  # "info" | "chat" | other
    thread_id: Optional[str] = Field(default=None, alias="threadId")
    run_id: Optional[str] = Field(default=None, alias="runId")
    messages: Optional[list[ChatMessage]] = None  # Optional for method="info"
    state: Optional[dict] = None  # Shared state from frontend


class ChatThreadResponse(BaseModel):
    """Response for thread reload endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    thread_id: str = Field(alias="threadId")
    messages: list[ChatMessage]
    state: Optional[dict] = None


def generate_message_id(conversation_id: str, message_index: int) -> str:
    """Generate stable message ID from conversation context."""
    return f"{conversation_id}:msg:{message_index}"


def generate_tool_call_id(run_id: str, tool_index: int) -> str:
    """Generate stable tool call ID."""
    return f"{run_id}:tool:{tool_index}"


def generate_step_id(run_id: str, step_index: int) -> str:
    """Generate stable step ID."""
    return f"{run_id}:step:{step_index}"
