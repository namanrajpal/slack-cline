# Implementation Plan: AG-UI + CopilotKit Dashboard Chat

[Overview]
Replace the AdminPanel test harness with a production-ready CopilotKit chat interface in the Dashboard, using AG-UI protocol for streaming agent responses.

This implementation transforms the Dashboard from a testing/debugging tool into the primary chat interface for Sline, alongside Slack. The architecture maintains a single agent runtime (SlineBrain) with two "front doors":
- **Slack Gateway** → Uses Slack formatting rules
- **Dashboard Chat** → Uses AG-UI events with CopilotKit UI

Both interfaces share the same `ConversationModel` for state persistence, ensuring consistent behavior across platforms. The LLM classifier continues to select projects automatically based on user questions.

**CopilotKit Pattern**: Using "Remote Endpoint" pattern - we have our own LangGraph agent (SlineBrain), we just need to stream AG-UI events back. No CopilotKit agent orchestration needed.

Key benefits:
- Rich streaming UI with tool call visualization
- Real-time token streaming (better UX than waiting for full response)
- Standard protocol (AG-UI) for future extensibility
- CopilotKit's battle-tested React components

**Critical Implementation Notes:**
- AG-UI spec uses **camelCase** field names (`messageId`, not `message_id`)
- Need **stable IDs** for messages/tools that persist across page reload
- Must implement **thread reload endpoint** for transcript recovery
- Use `astream_events()` for real-time streaming

[Types]

New types for AG-UI event translation with camelCase field aliases.

**Backend Types (`backend/schemas/agui.py`):**

```python
"""
AG-UI Protocol event types for CopilotKit compatibility.

IMPORTANT: AG-UI spec uses camelCase in JSON output.
Use Field(alias=...) for camelCase serialization while keeping
Pythonic snake_case in code.

Ref: https://docs.ag-ui.com/concepts/events
"""

from enum import StrEnum
from typing import Optional, Any
from datetime import datetime
from uuid import uuid4
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
    
    # State events (optional, for CopilotKit shared state)
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


class CopilotKitMessage(BaseModel):
    """CopilotKit message format for thread reload."""
    model_config = ConfigDict(populate_by_name=True)
    
    id: str
    role: str  # "user" | "assistant"
    content: str
    created_at: Optional[str] = Field(default=None, alias="createdAt")


class CopilotKitRequest(BaseModel):
    """CopilotKit chat request structure."""
    model_config = ConfigDict(populate_by_name=True)
    
    thread_id: Optional[str] = Field(default=None, alias="threadId")
    run_id: Optional[str] = Field(default=None, alias="runId")
    messages: list[CopilotKitMessage]
    state: Optional[dict] = None  # Shared state from frontend


class CopilotKitThreadResponse(BaseModel):
    """Response for thread reload endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    thread_id: str = Field(alias="threadId")
    messages: list[CopilotKitMessage]
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
```

**Frontend Types (`frontend/src/types/agui.ts`):**

```typescript
// AG-UI event types (for reference, CopilotKit handles these internally)
export type AGUIEventType =
  | 'runStarted'
  | 'runFinished'
  | 'runError'
  | 'stepStarted'
  | 'stepFinished'
  | 'textMessageStart'
  | 'textMessageContent'
  | 'textMessageEnd'
  | 'toolCallStart'
  | 'toolCallArgs'
  | 'toolCallEnd';

// CopilotKit shared state for project context (future use)
export interface CopilotSharedState {
  selectedProjectId?: string;
  selectedProjectName?: string;
}
```

[Files]

File modifications for AG-UI + CopilotKit integration.

**New Backend Files:**
- `backend/schemas/agui.py` - AG-UI event types with camelCase aliases
- `backend/modules/copilotkit/__init__.py` - Module init
- `backend/modules/copilotkit/routes.py` - CopilotKit HTTP endpoints (chat + thread reload)
- `backend/modules/copilotkit/event_translator.py` - LangChain → AG-UI event translation
- `backend/modules/copilotkit/sse_utils.py` - SSE encoding helper

**Modified Backend Files:**
- `backend/modules/agent/service.py` - Add `handle_message_streaming()` method
- `backend/main.py` - Register CopilotKit router

**New Frontend Files:**
- `frontend/src/types/agui.ts` - AG-UI TypeScript types
- `frontend/src/components/chat/ChatPanel.tsx` - CopilotKit chat wrapper
- `frontend/src/lib/copilotkit.ts` - CopilotKit configuration helpers

**Modified Frontend Files:**
- `frontend/package.json` - Add CopilotKit dependencies (latest stable)
- `frontend/src/App.tsx` - Add CopilotKitProvider
- `frontend/src/pages/Dashboard.tsx` - Embed ChatPanel component
- `frontend/src/components/Sidebar.tsx` - Remove AdminPanel nav item

**Deleted Frontend Files:**
- `frontend/src/pages/AdminPanel.tsx` - Replace with Dashboard chat

[Functions]

Function modifications for streaming AG-UI support.

**New Backend Functions:**

`backend/modules/agent/service.py`:
```python
async def handle_message_streaming(
    self,
    channel_id: str,
    thread_ts: str,
    user_id: str,
    text: str,
    session: AsyncSession,
) -> AsyncIterator[AGUIEvent]:
    """
    Handle message with streaming AG-UI events.
    
    Uses astream_events() instead of ainvoke() for real-time streaming.
    Yields AG-UI events for CopilotKit consumption.
    
    ID Stability:
    - messageId = f"{conversation_id}:msg:{index}" (deterministic)
    - toolCallId = LangGraph tool call ID or f"{run_id}:tool:{index}"
    - stepId = f"{run_id}:step:{index}"
    """
```

`backend/modules/copilotkit/sse_utils.py`:
```python
def encode_sse(event: AGUIEvent) -> str:
    """
    Encode AG-UI event as standard SSE frame.
    
    Format:
        data: {"type":"textMessageContent",...}\n\n
    """
    json_str = event.model_dump_json(by_alias=True, exclude_none=True)
    return f"data: {json_str}\n\n"


async def sse_generator(events: AsyncIterator[AGUIEvent]) -> AsyncIterator[str]:
    """Async generator that encodes events to SSE strings."""
    async for event in events:
        yield encode_sse(event)
```

`backend/modules/copilotkit/event_translator.py`:
```python
def translate_langchain_event(
    event: dict,
    run_id: str,
    message_id: str,
    tool_counter: dict,
    step_counter: dict,
) -> Optional[AGUIEvent]:
    """
    Translate LangChain astream_events() output to AG-UI format.
    
    Maps:
    - on_chat_model_stream → textMessageContent
    - on_chat_model_start → textMessageStart
    - on_chat_model_end → textMessageEnd
    - on_tool_start → toolCallStart
    - on_tool_end → toolCallEnd
    - on_chain_start → stepStarted
    - on_chain_end → stepFinished
    
    Uses counters to generate stable IDs for tools/steps.
    """

async def stream_agui_events(
    graph,
    state: SlineState,
    thread_id: str,
    run_id: str,
    message_index: int,
) -> AsyncIterator[AGUIEvent]:
    """
    Stream AG-UI events from LangGraph execution.
    
    Wraps graph.astream_events() and translates to AG-UI.
    Emits runStarted at beginning, runFinished/runError at end.
    """
```

`backend/modules/copilotkit/routes.py`:
```python
@router.post("/")
async def copilotkit_chat(
    request: CopilotKitRequest,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """
    CopilotKit-compatible chat endpoint (Remote Endpoint pattern).
    
    Accepts CopilotKit protocol requests, invokes agent,
    streams AG-UI events back via SSE.
    
    Response headers:
    - Content-Type: text/event-stream
    - Cache-Control: no-cache
    - Connection: keep-alive
    """

@router.get("/thread/{thread_id}")
async def get_thread(
    thread_id: str,
    session: AsyncSession = Depends(get_session),
) -> CopilotKitThreadResponse:
    """
    Return persisted transcript for CopilotKit thread reload.
    
    Returns messages in exact shape CopilotKit expects,
    with stable messageIds that match what was streamed.
    """
```

**Modified Backend Functions:**

`backend/modules/agent/service.py`:
- `_get_or_create_state()` - Handle dashboard-generated thread_ts (UUID format)

**New Frontend Functions:**

`frontend/src/lib/copilotkit.ts`:
```typescript
export function getCopilotKitConfig() {
  return {
    runtimeUrl: `${import.meta.env.VITE_API_URL}/api/copilotkit`,
  };
}

export function generateThreadId(): string {
  return crypto.randomUUID();
}
```

`frontend/src/components/chat/ChatPanel.tsx`:
```typescript
export function ChatPanel({ className }: { className?: string }) {
  // Wraps CopilotChat with Sline styling
  // Manages thread_id in local state or URL
}
```

[Classes]

Class modifications for streaming support.

**Modified Classes:**

`backend/modules/agent/service.py - AgentService`:
- Add `handle_message_streaming()` method
- Keep existing `handle_message()` for Slack (non-streaming)
- Both methods use same `_get_or_create_state()` and `_save_state()`
- Store message_index in conversation state for stable ID generation

No new classes required - using functional approach for event translation.

[Dependencies]

Dependency modifications for CopilotKit integration.

**Backend (`requirements.txt`):**
```
# Add:
sse-starlette>=2.0.0  # SSE support for FastAPI
```

Note: LangGraph already supports `astream_events()` - no additional LangChain deps needed.

**Frontend (`package.json`):**
```json
{
  "dependencies": {
    "@copilotkit/react-core": "latest",
    "@copilotkit/react-ui": "latest"
  }
}
```

**Important**: Use latest stable versions at install time, not hardcoded versions.
Run: `npm install @copilotkit/react-core @copilotkit/react-ui`

[Testing]

Testing approach for AG-UI streaming integration.

**Pre-flight Checklist (Critical):**
- ✅ Stable `threadId` stored in DB and reused after refresh
- ✅ Stable `messageId` per assistant message; deltas reference same id
- ✅ Tool call IDs stable within a run
- ✅ SSE flushes incrementally (no buffering behind proxy)
- ✅ CORS + credentials configured (Dashboard ↔ backend)
- ✅ All AG-UI events use camelCase field names

**Manual Testing:**
1. Start backend with `docker-compose up`
2. Start frontend with `npm run dev`
3. Open Dashboard at `http://localhost:3001`
4. Send message in CopilotKit chat
5. Verify:
   - Streaming text appears incrementally (not buffered)
   - Tool calls show in UI with proper names/results
   - Conversation persists across page refresh
   - Thread reload returns correct transcript

**Backend Testing:**
```bash
# Test SSE endpoint with curl
curl -N -X POST http://localhost:8000/api/copilotkit \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"id":"1","role":"user","content":"Hello"}]}'

# Test thread reload
curl http://localhost:8000/api/copilotkit/thread/test-thread-id
```

**Verify AG-UI event format:**
```json
{"type":"runStarted","threadId":"abc","runId":"xyz"}
{"type":"textMessageStart","messageId":"abc:msg:0","role":"assistant"}
{"type":"textMessageContent","messageId":"abc:msg:0","delta":"Hello"}
{"type":"textMessageEnd","messageId":"abc:msg:0"}
{"type":"runFinished","threadId":"abc","runId":"xyz"}
```

**Integration Testing:**
- Send message via Dashboard, verify in database
- Refresh page, verify transcript loads correctly
- Send message via Slack to same thread, verify continuity

[Implementation Order]

Sequential implementation steps to minimize conflicts.

1. **Backend: Add AG-UI schema types** (20 min)
   - Create `backend/schemas/agui.py`
   - Define event types with camelCase Field aliases
   - Add ID generation helpers

2. **Backend: Add SSE utilities** (10 min)
   - Create `backend/modules/copilotkit/sse_utils.py`
   - Implement `encode_sse()` helper

3. **Backend: Create event translator** (45 min)
   - Create `backend/modules/copilotkit/event_translator.py`
   - Map LangChain events → AG-UI events
   - Handle step boundaries (chain start/end)
   - Test event output format

4. **Backend: Add streaming to AgentService** (30 min)
   - Add `handle_message_streaming()` method to `service.py`
   - Use `graph.astream_events()` instead of `ainvoke()`
   - Yield events through translator

5. **Backend: Create CopilotKit routes** (30 min)
   - Create `backend/modules/copilotkit/routes.py`
   - Implement `POST /api/copilotkit` (SSE streaming)
   - Implement `GET /api/copilotkit/thread/{thread_id}` (reload)
   - Register router in `main.py`

6. **Backend: Test streaming endpoint** (15 min)
   - Test with curl to verify SSE format
   - Verify camelCase field names
   - Test thread reload endpoint

7. **Frontend: Add CopilotKit dependencies** (10 min)
   - `npm install @copilotkit/react-core @copilotkit/react-ui`
   - Add types file

8. **Frontend: Add CopilotKitProvider** (15 min)
   - Wrap app in `App.tsx`
   - Configure runtime URL

9. **Frontend: Create ChatPanel component** (30 min)
   - Create `components/chat/ChatPanel.tsx`
   - Integrate CopilotChat with Sline styling
   - Handle thread_id generation/storage

10. **Frontend: Embed chat in Dashboard** (20 min)
    - Modify `pages/Dashboard.tsx`
    - Add ChatPanel alongside existing stats

11. **Frontend: Remove AdminPanel** (10 min)
    - Delete `pages/AdminPanel.tsx`
    - Remove route from `App.tsx`
    - Remove nav item from `Sidebar.tsx`

12. **End-to-end testing** (30 min)
    - Test full flow: Dashboard → Backend → Agent → Streaming response
    - Test page refresh (thread reload)
    - Test multi-turn conversations
    - Verify stable IDs across refresh

**Total Estimated Time: ~4.5 hours**

---

## Gotchas Checklist

Before marking complete, verify:

- [ ] AG-UI events use camelCase (`messageId` not `message_id`)
- [ ] Stable `threadId` stored in DB, reused after refresh
- [ ] Stable `messageId` per message, deltas reference same id
- [ ] Tool call IDs stable within a run
- [ ] SSE flushes incrementally (check no proxy buffering)
- [ ] CORS configured for Dashboard origin
- [ ] Thread reload returns exact message shapes CopilotKit expects
- [ ] Step events map from LangGraph chain boundaries
