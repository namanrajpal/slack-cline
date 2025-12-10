# Implementation Plan

[Product Vision]
Sline is your AI coding teammate that lives in Slack - a collaborative partner that thinks, plans, and codes alongside your team.

### 🎯 The Core Experience

**Sline isn't a bot you command - it's a teammate you collaborate with.**

Imagine this workflow:
```
#frontend-team channel

👤 Alice: Hey team, we need to add dark mode support. @sline what do you think?

🤖 Sline: Hey! 👋 Looking at the codebase, I see you're using Tailwind CSS 
         with a theme provider in `src/context/ThemeContext.tsx`. 
         
         Here's what I'd suggest:
         1. Add dark mode classes to your tailwind.config.js
         2. Update the ThemeContext to persist preference
         3. Add a toggle component
         
         Want me to create a detailed implementation plan?

👤 Bob: We also need to make sure it respects system preferences

🤖 Sline: Good point Bob! I'll include `prefers-color-scheme` media query 
         detection. The ThemeContext can check this on mount.

👤 Alice: Sounds good. @sline create an impl plan

🤖 Sline: 📋 **Implementation Plan: Dark Mode Support**
         
         **Step 1: Update Tailwind Config** (5 min)
         - Add `darkMode: 'class'` to tailwind.config.js
         - Define dark color palette
         
         **Step 2: Enhance ThemeContext** (15 min)
         - Add system preference detection
         - Persist to localStorage
         - Sync across tabs
         
         **Step 3: Create Toggle Component** (10 min)
         - Add ThemeToggle.tsx with icon states
         - Wire to context
         
         [✅ Approve & Execute] [✏️ Modify] [❌ Cancel]

👤 Alice: ✅ Approved

🤖 Sline: 🚀 On it! Starting with the Tailwind config...
         ✅ Step 1 complete - tailwind.config.js updated
         ✅ Step 2 complete - ThemeContext.tsx enhanced  
         ✅ Step 3 complete - ThemeToggle.tsx created
         
         All done! 🎉 Run `npm run dev` to test the dark mode toggle.
```

### 💡 Key UX Principles

1. **Conversational, Not Transactional**
   - Sline participates in the discussion like a team member
   - Other teammates can add context, correct Sline, or suggest alternatives
   - Natural back-and-forth before any code changes

2. **Plan → Approve → Execute**
   - Sline NEVER makes changes without explicit approval
   - Shows clear, reviewable plans with specific files and steps
   - Team can discuss the plan before approving

3. **Aware of Team Context**
   - Sline sees what teammates say in the thread
   - Can incorporate feedback from multiple people
   - Knows when to wait for team consensus

4. **Friendly & Helpful Tone**
   - Uses casual but professional language
   - Adds relevant emoji sparingly (✅ 🔧 📁)
   - Celebrates wins with the team
   - Asks clarifying questions when needed

### 🎭 Sline's Personality

From `.clinerules/sline-personality.md`:
- Always refers to itself as "Sline" (not "I" or "the assistant")
- Friendly AI coding teammate
- Concise responses (Slack favors brevity)
- Provides code references with file paths
- Signs off team-friendly: "All done! ✅" not "Task completed successfully."

### 📊 Slack Thread as Collaboration Space

```
Thread Structure:
├── Original message (triggers Sline)
├── 👤 Teammate comments / questions
├── 🤖 Sline responds, asks for clarity
├── 👤 More discussion...
├── 👤 "Create impl plan"
├── 🤖 Sline posts plan with buttons
├── 👤 Approves / Modifies
└── 🤖 Sline executes and reports
```

The thread IS the conversation history - Sline remembers everything said in that thread.

---

[Overview]
Replace Cline CLI subprocess integration with a native LangGraph-based "SlineBrain" agent that provides the same coding assistant capabilities directly in Python.

Sline v2 migrates from the complex Cline CLI orchestration (subprocess calls, task create/run/view, instance management) to a simple, direct Python implementation using LangGraph. The core concept is a **single ReAct-style agent called SlineBrain** that all workflow modes (chat, plan, execute) call with different instructions. This gives full control over the UX and eliminates the dependency on external CLI tools.

**Key Benefits:**
- No more subprocess calls or CLI output parsing
- Full control over conversation flow and UX
- Simpler state management via LangGraph
- Same tools as Cline (read_file, search_files, etc.) but in native Python
- "Chatty teammate" personality optimized for Slack

**Architecture Pattern:**
- SlineBrain = Single ReAct agent with tools (handles multi-step reasoning)
- Workflow nodes = Thin wrappers that call SlineBrain with mode-specific instructions
- Graph = State machine managing chat → plan → approve → execute transitions

**What We Keep:**
- FastAPI backend infrastructure
- Slack Gateway (simplified to call agent directly)
- Dashboard API and frontend
- PostgreSQL database
- Project model (channel → repo mapping)

**What We Remove:**
- `modules/execution_engine/` (Cline CLI client)
- `modules/orchestrator/` (complex run lifecycle)
- Cline CLI dependency in Docker
- Complex "Run" model tied to Cline concepts

**What We Add:**
- `modules/agent/` (new SlineBrain module)
- Native Python tools for file operations
- Conversation model for thread history
- Simplified session tracking

[Types]
Define TypedDict for LangGraph state, Pydantic models for database entities, and tool input schemas.

### SlineState (LangGraph State)

```python
# backend/modules/agent/state.py
from typing import Optional, Literal, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class SlineState(TypedDict):
    """State object passed through the LangGraph workflow.
    
    Initial state for new conversations should set:
    - mode = "chat" (default starting mode)
    - messages = [] (empty list)
    - All context fields from project/Slack
    """
    
    # Conversation messages with reducer for appending
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
```

### Conversation Model (Database)

```python
# backend/models/conversation.py
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database import Base
import uuid

class ConversationModel(Base):
    """Stores conversation state per Slack thread."""
    
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Slack identifiers (composite unique constraint)
    channel_id = Column(String(255), nullable=False, index=True)
    thread_ts = Column(String(255), nullable=False, index=True)
    
    # Link to project
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    
    # Serialized state (JSON blob of SlineState)
    state_json = Column(JSON, nullable=False, default=dict)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_user_id = Column(String(255))  # Last user who interacted
    message_count = Column(Integer, default=0)
    
    __table_args__ = (
        UniqueConstraint("channel_id", "thread_ts", name="uix_channel_thread"),
    )
```

### Tool Input Schemas

```python
# backend/modules/agent/tools/schemas.py
from pydantic import BaseModel, Field
from typing import Optional

class ReadFileInput(BaseModel):
    """Input schema for read_file tool."""
    path: str = Field(description="Relative path to the file to read")

class SearchFilesInput(BaseModel):
    """Input schema for search_files tool."""
    path: str = Field(description="Directory path to search in")
    regex: str = Field(description="Regular expression pattern to search for")
    file_pattern: Optional[str] = Field(default="*", description="Glob pattern to filter files")

class ListFilesInput(BaseModel):
    """Input schema for list_files tool."""
    path: str = Field(description="Directory path to list")
    recursive: bool = Field(default=False, description="Whether to list recursively")

class WriteFileInput(BaseModel):
    """Input schema for write_to_file tool (Phase 2)."""
    path: str = Field(description="Relative path to the file to write")
    content: str = Field(description="Content to write to the file")

class ExecuteCommandInput(BaseModel):
    """Input schema for execute_command tool (Phase 2)."""
    command: str = Field(description="CLI command to execute")
    requires_approval: bool = Field(default=True, description="Whether command needs approval")
```

### Session Model (Phase 2+ - Not needed for MVP)

**Note: SessionModel is deferred to Phase 2+. For MVP, ConversationModel is sufficient for state persistence. SessionModel can be added later for dashboard analytics, usage tracking, and token cost monitoring.**

```python
# backend/models/session.py (PHASE 2+)
# This model is NOT needed for MVP - add when implementing dashboard analytics
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database import Base
import uuid
import enum

class SessionStatus(enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"

class SessionModel(Base):
    """Simplified session tracking for analytics (Phase 2+)."""
    
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE)
    initial_prompt = Column(Text)
    summary = Column(Text)
    
    created_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
    
    tool_calls_count = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
```

[Files]
New files to create, existing files to modify, and files to remove.

### New Files to Create

```
backend/modules/agent/
├── __init__.py                    # Module exports
├── state.py                       # SlineState TypedDict definition
├── prompts.py                     # System prompts (BASE_SYSTEM_PROMPT, mode instructions)
├── brain.py                       # SlineBrain ReAct agent creation
├── graph.py                       # LangGraph state machine (nodes, edges)
├── nodes.py                       # Node functions (chat_node, plan_node, etc.)
├── service.py                     # AgentService class (main interface for Slack gateway)
└── tools/
    ├── __init__.py                # Tool exports
    ├── factory.py                 # make_bound_tools() - creates tools with workspace bound
    ├── schemas.py                 # Pydantic input schemas (optional, for API validation)
    └── (Phase 2+)
        ├── code_tools.py          # list_code_definitions (tree-sitter)
        └── command_tools.py       # execute_command (subprocess)

backend/models/
├── conversation.py                # NEW: ConversationModel
└── session.py                     # NEW: SessionModel (simplified from run.py)

backend/schemas/
└── conversation.py                # NEW: Pydantic schemas for conversation API
```

### Existing Files to Modify

```
backend/modules/slack_gateway/handlers.py
  - Remove: orchestrator imports and calls
  - Add: agent service imports
  - Modify: handle_cline_command() to call AgentService instead
  - Modify: handle_event_callback() for thread replies via agent

backend/database.py
  - Add: Import new models (ConversationModel, SessionModel)

backend/main.py
  - Remove: orchestrator cleanup
  - Add: agent service initialization

backend/config.py
  - Remove: Cline CLI-specific settings (if any)
  - Keep: LLM provider settings (CLINE_PROVIDER, CLINE_API_KEY, etc.)

backend/requirements.txt (or requirements.txt at root)
  - Add: langchain>=0.3.0
  - Add: langgraph>=0.2.0
  - Add: langchain-openai>=0.2.0
  - Add: langchain-anthropic>=0.2.0

docker-compose.yml
  - Remove: Cline CLI installation steps (if in Dockerfile)
  - Keep: Python backend service

Dockerfile
  - Remove: npm install -g cline
  - Remove: Node.js installation (if only for Cline)
  - Keep: Python environment
```

### Files to Remove

```
backend/modules/execution_engine/
├── cli_client.py                  # DELETE: Cline CLI wrapper
└── translator.py                  # DELETE: Event translation

backend/modules/orchestrator/
└── service.py                     # DELETE: Complex run orchestration

backend/models/run.py              # DELETE (or rename to session.py)
backend/schemas/run.py             # DELETE (or simplify for session)
```

### Files to Keep Unchanged

```
backend/modules/dashboard/         # Keep all dashboard API
backend/modules/slack_gateway/verification.py  # Keep signature verification
backend/models/project.py          # Keep project model
backend/utils/logging.py           # Keep logging utils
backend/utils/slack_client.py      # Keep Slack client utils
frontend/                          # Keep entire frontend
```

[Functions]
New functions to implement and existing functions to modify.

### New Functions

**brain.py - SlineBrain Creation**

**Important Architecture Notes:**
- SlineBrain is a **compiled ReAct agent** from `create_react_agent()`, not a raw LLM
- Tools must have `workspace_path` **bound** (not exposed to LLM) - see tools/factory.py
- Create SlineBrain **per-conversation** since tools are bound to workspace_path
- Use `ainvoke()` for async operations in nodes

```python
# backend/modules/agent/brain.py
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from config import settings
from .tools.factory import make_bound_tools
from .prompts import BASE_SYSTEM_PROMPT

def get_llm_model():
    """Get LLM model based on config (singleton)."""
    if settings.cline_provider == "anthropic":
        return ChatAnthropic(
            model=settings.cline_model_id,
            api_key=settings.cline_api_key
        )
    elif settings.cline_provider in ("openai-native", "openai"):
        return ChatOpenAI(
            model=settings.cline_model_id,
            api_key=settings.cline_api_key
        )
    # Add more providers as needed
    raise ValueError(f"Unsupported provider: {settings.cline_provider}")

def create_sline_brain(workspace_path: str):
    """
    Create SlineBrain ReAct agent with tools bound to workspace.
    
    This is called ONCE per conversation (since workspace_path varies per project).
    The resulting agent handles multi-step tool use via ReAct pattern.
    
    Args:
        workspace_path: Absolute path to cloned repo workspace
    
    Returns:
        CompiledGraph: LangGraph ReAct agent ready for ainvoke()
    """
    model = get_llm_model()
    tools = make_bound_tools(workspace_path)  # Tools with workspace bound
    
    return create_react_agent(
        model=model,
        tools=tools,
        # System prompt can be passed here or in messages per-node
    )
```

**nodes.py - Workflow Nodes**
```python
async def chat_node(state: SlineState) -> dict:
    """
    Handle normal chat: questions, explanations, light suggestions.
    Calls SlineBrain with chat mode instructions.
    Returns updated messages and maintains mode="chat".
    """

async def plan_node(state: SlineState) -> dict:
    """
    Generate implementation plan using SlineBrain.
    Calls SlineBrain with planning mode instructions.
    Returns updated messages, sets plan text, mode="awaiting_approval".
    """

async def execute_node(state: SlineState) -> dict:
    """
    Execute approved plan using SlineBrain (or deterministic steps).
    Calls SlineBrain with execute mode instructions.
    Returns updated messages, mode="completed" or "error".
    """

def route_from_chat(state: SlineState) -> str:
    """
    Conditional edge: decide if we stay in chat or go to planning.
    Examines last message for intent keywords.
    Returns: "plan" | "end"
    """
```

**graph.py - LangGraph Assembly**
```python
def create_sline_graph() -> CompiledStateGraph:
    """
    Create and compile the Sline workflow graph.
    
    Nodes: chat, plan, await_approval, execute
    Edges: chat -> plan (conditional), plan -> await_approval, 
           await_approval -> execute (on approval), execute -> chat
    
    Returns:
        Compiled StateGraph ready for .invoke() or .stream()
    """
```

**service.py - Main Interface**
```python
class AgentService:
    """Service layer for Sline agent, called by Slack gateway."""
    
    async def handle_message(
        self,
        channel_id: str,
        thread_ts: str,
        user_id: str,
        text: str,
        session: AsyncSession
    ) -> AsyncIterator[str]:
        """
        Handle incoming Slack message.
        Loads conversation state, invokes graph, saves state, yields responses.
        """
    
    async def handle_approval(
        self,
        channel_id: str,
        thread_ts: str,
        approved: bool,
        session: AsyncSession
    ) -> str:
        """
        Handle plan approval/rejection from Slack button click.
        """
    
    async def get_or_create_conversation(
        self,
        channel_id: str,
        thread_ts: str,
        project_id: str,
        session: AsyncSession
    ) -> ConversationModel:
        """
        Get existing conversation or create new one.
        """
    
    def state_to_json(self, state: SlineState) -> dict:
        """Serialize SlineState to JSON for database storage."""
    
    def json_to_state(self, json_data: dict) -> SlineState:
        """Deserialize JSON from database to SlineState."""
```

**tools/factory.py - Bound Tools Factory**

**Critical Design: Tools should NOT expose `workspace_path` to the LLM.**

The LLM should only see user-facing parameters (`path`, `regex`, etc.). `workspace_path` is internal context that should be bound via closure.

```python
# backend/modules/agent/tools/factory.py
import os
from pathlib import Path
from langchain_core.tools import tool

def make_bound_tools(workspace_path: str) -> list:
    """
    Create tools with workspace_path already bound.
    
    This factory creates tool functions that close over workspace_path,
    so the LLM only sees user-facing parameters like 'path' and 'regex'.
    
    Args:
        workspace_path: Absolute path to the workspace (cloned repo)
    
    Returns:
        List of LangChain tools ready for create_react_agent()
    """
    
    @tool
    def read_file(path: str) -> str:
        """Read contents of a file at the given path.
        
        Args:
            path: Relative path to the file (e.g., 'src/main.py')
        
        Returns:
            File contents as string, or error message if file not found
        """
        abs_path = os.path.join(workspace_path, path)
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: File not found: {path}"
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    @tool
    def list_files(path: str = ".", recursive: bool = False) -> str:
        """List files and directories at the given path.
        
        Args:
            path: Directory path to list (default: workspace root)
            recursive: If True, list all files recursively
        
        Returns:
            Formatted list of files/directories
        """
        abs_path = os.path.join(workspace_path, path)
        try:
            if recursive:
                files = []
                for root, dirs, filenames in os.walk(abs_path):
                    for f in filenames:
                        rel = os.path.relpath(os.path.join(root, f), workspace_path)
                        files.append(rel)
                return "\n".join(sorted(files))
            else:
                entries = os.listdir(abs_path)
                return "\n".join(sorted(entries))
        except Exception as e:
            return f"Error listing files: {str(e)}"
    
    @tool
    def search_files(regex: str, path: str = ".", file_pattern: str = "*") -> str:
        """Search for a regex pattern across files in a directory.
        
        Args:
            regex: Regular expression pattern to search for
            path: Directory to search in (default: workspace root)
            file_pattern: Glob pattern to filter files (e.g., '*.py')
        
        Returns:
            Search results with file paths, line numbers, and matching lines
        """
        import re
        from pathlib import Path
        
        abs_path = os.path.join(workspace_path, path)
        results = []
        pattern = re.compile(regex)
        
        try:
            for file_path in Path(abs_path).rglob(file_pattern):
                if file_path.is_file():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for i, line in enumerate(f, 1):
                                if pattern.search(line):
                                    rel_path = os.path.relpath(file_path, workspace_path)
                                    results.append(f"{rel_path}:{i}: {line.rstrip()}")
                    except (UnicodeDecodeError, PermissionError):
                        continue
            
            if results:
                return "\n".join(results[:50])  # Limit results
            return "No matches found."
        except Exception as e:
            return f"Error searching: {str(e)}"
    
    # Return all tools as a list
    return [read_file, list_files, search_files]
```

**Phase 2 Tools (add to factory later):**
```python
    @tool
    def write_to_file(path: str, content: str) -> str:
        """Write content to a file (creates directories if needed).
        
        Args:
            path: Relative path for the file
            content: Content to write
        """
        abs_path = os.path.join(workspace_path, path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
```

### Existing Functions to Modify

**slack_gateway/handlers.py**
```python
# MODIFY: handle_cline_command()
# Before: Creates StartRunCommand, calls orchestrator.start_run()
# After: Calls AgentService.handle_message()

async def handle_cline_command(
    command_data: SlackCommandSchema, 
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """
    Handle /cline slash command.
    
    CHANGES:
    - Remove StartRunCommand creation
    - Remove orchestrator import and call
    - Add AgentService import
    - Call agent_service.handle_message() directly
    - Stream responses to Slack
    """

# MODIFY: handle_event_callback()
# Before: Calls orchestrator for thread replies
# After: Calls AgentService.handle_message()

# MODIFY: process_thread_reply()
# Before: Uses orchestrator.handle_thread_reply()
# After: Uses agent_service.handle_message()
```

**main.py**
```python
# MODIFY: Remove orchestrator cleanup
# ADD: Agent service initialization (if needed)

@app.on_event("shutdown")
async def shutdown_event():
    # REMOVE: await cleanup_orchestrator_service()
    pass
```

[Classes]
New classes and modifications to existing classes.

### New Classes

**AgentService (backend/modules/agent/service.py)**
```python
class AgentService:
    """
    Main service class for Sline agent.
    
    Responsibilities:
    - Load/save conversation state from database
    - Initialize and invoke LangGraph
    - Translate between Slack messages and agent state
    - Handle streaming responses back to Slack
    
    Attributes:
        graph: CompiledStateGraph - The Sline workflow graph
        slack_client: SlackClient - For posting messages
        
    Methods:
        handle_message() - Main entry point for Slack messages
        handle_approval() - Handle approval button clicks
        get_or_create_conversation() - Conversation state management
    """
```

**ConversationModel (backend/models/conversation.py)**
```python
class ConversationModel(Base):
    """
    SQLAlchemy model for conversation persistence.
    
    Purpose: Store SlineState per Slack thread for conversation continuity.
    
    Key Fields:
    - channel_id + thread_ts: Unique identifier
    - state_json: Serialized SlineState
    - project_id: Link to project for workspace context
    """
```

**SessionModel (backend/models/session.py)**
```python
class SessionModel(Base):
    """
    Simplified session tracking (replaces RunModel).
    
    Purpose: Track agent sessions for dashboard/analytics.
    Not tied to Cline CLI concepts.
    """
```

### Classes to Remove

**RunModel (backend/models/run.py)**
- DELETE: Entire class
- Reason: Tied to Cline CLI concepts (instance_address, workspace_path, cline_run_id)
- Replacement: SessionModel for analytics, ConversationModel for state

**ClineCliClient (backend/modules/execution_engine/cli_client.py)**
- DELETE: Entire class
- Reason: Cline CLI subprocess wrapper no longer needed

**RunOrchestratorService (backend/modules/orchestrator/service.py)**
- DELETE: Entire class
- Reason: Complex orchestration replaced by LangGraph state machine

### Classes to Modify

**SlackClient (backend/utils/slack_client.py)**
```python
# ADD: Method for posting agent responses with formatting
async def post_agent_response(
    self,
    channel: str,
    thread_ts: str,
    text: str,
    blocks: list = None
) -> dict:
    """Post agent response with Slack mrkdwn formatting."""
```

[Dependencies]
New packages to add and packages to remove.

### Add to requirements.txt

```
# LangChain / LangGraph
langchain>=0.3.0
langgraph>=0.2.0
langchain-core>=0.3.0

# LLM Providers
langchain-openai>=0.2.0        # For OpenAI/OpenRouter
langchain-anthropic>=0.2.0     # For Anthropic Claude

# Optional: Code analysis (Phase 3)
# tree-sitter>=0.21.0
# tree-sitter-python>=0.21.0
```

### Keep (no changes)

```
fastapi
uvicorn
sqlalchemy[asyncio]
asyncpg
pydantic>=2.0
python-dotenv
structlog
httpx
slack-sdk
```

### Remove (if only used by Cline)

```
# If Node.js was installed only for Cline CLI, remove from Dockerfile:
# - Node.js installation
# - npm install -g cline
```

### Dockerfile Changes

```dockerfile
# REMOVE these lines:
# RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
# RUN apt-get install -y nodejs
# RUN npm install -g cline

# KEEP Python-only image:
FROM python:3.12-slim

# Keep git for cloning repos
RUN apt-get update && apt-get install -y git

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/
WORKDIR /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

[Testing]
Testing approach for the new agent system.

### Unit Tests

```
backend/modules/agent/tests/
├── test_tools.py          # Test file_tools, search_tools independently
├── test_nodes.py          # Test each node function with mock SlineBrain
├── test_graph.py          # Test graph transitions
└── test_service.py        # Test AgentService with mock database
```

**Key Test Cases:**

1. **Tool Tests (test_tools.py)**
   - read_file returns correct content
   - read_file handles missing files gracefully
   - list_files returns correct format
   - search_files finds matches with context

2. **Node Tests (test_nodes.py)**
   - chat_node calls SlineBrain and returns AI message
   - plan_node sets mode to "awaiting_approval"
   - execute_node handles tool errors gracefully

3. **Graph Tests (test_graph.py)**
   - Initial state routes to chat_node
   - Intent detection triggers planning mode
   - Approval transitions to execute

4. **Service Tests (test_service.py)**
   - Conversation created for new thread
   - State persisted after each message
   - State restored on subsequent messages

### Integration Testing via Admin Panel

The existing Admin Panel (`/admin`) can be used to test the full flow:

1. Select a channel with configured project
2. Send test messages:
   - "What does the main.py file do?" (triggers read_file)
   - "Search for TODO comments" (triggers search_files)
   - "Add logging to the auth module" (should trigger planning)
3. Verify responses appear correctly
4. Check database for conversation state

### Manual Testing Checklist

```
- [ ] Send question → Agent uses tools to answer
- [ ] Multi-turn conversation → State preserved
- [ ] Thread reply → Continues same conversation
- [ ] Error in tool → Graceful error message
- [ ] Long response → Properly chunked for Slack
- [ ] Plan request → Shows plan with approval buttons
- [ ] Approve plan → Executes changes
- [ ] Reject plan → Returns to chat mode
```

[Implementation Order]
Step-by-step implementation sequence for Phase 1 MVP.

### Phase 1: Core Agent (MVP) - Estimated 4-6 hours

**Step 1: Create Agent Module Structure**
- Create `backend/modules/agent/` directory
- Create `__init__.py`, `state.py`, `prompts.py`
- Define SlineState TypedDict
- Write BASE_SYSTEM_PROMPT

**Step 2: Implement Bound Tools Factory**
- Create `backend/modules/agent/tools/`
- Create `factory.py` with `make_bound_tools(workspace_path)`
- Implement bound `read_file` tool (workspace_path closed over)
- Implement bound `list_files` tool
- Implement bound `search_files` tool
- Tools should NOT expose workspace_path to LLM

**Step 3: Create SlineBrain**
- Create `backend/modules/agent/brain.py`
- Configure LLM (use existing CLINE_PROVIDER config)
- Create ReAct agent with tools using `create_react_agent()`
- Test brain invocation independently

**Step 4: Create LangGraph Workflow**
- Create `backend/modules/agent/nodes.py`
- Implement `chat_node` (MVP: chat only)
- Create `backend/modules/agent/graph.py`
- Wire nodes into StateGraph
- Test graph invocation

**Step 5: Create AgentService**
- Create `backend/modules/agent/service.py`
- Implement `handle_message()` method
- Implement state serialization/deserialization
- Add conversation loading (in-memory for MVP, DB in step 7)

**Step 6: Wire to Slack Gateway**
- Modify `backend/modules/slack_gateway/handlers.py`
- Replace orchestrator calls with AgentService calls
- Update `handle_cline_command()` 
- Update `process_thread_reply()`
- Remove orchestrator imports

**Step 7: Add Conversation Persistence**
- Create `backend/models/conversation.py`
- Add ConversationModel to database.py
- Update AgentService to load/save state
- Run migration or recreate database

**Step 8: Test End-to-End**
- Start services: `docker-compose up`
- Use Admin Panel to test
- Verify tool calls work
- Verify multi-turn conversation
- Verify state persistence

### Phase 2: Planning & Approval (After MVP validated)

**Step 9: Add Plan Node**
- Implement `plan_node` in nodes.py
- Add conditional routing from chat to plan
- Update graph.py with plan node

**Step 10: Add Approval Flow**
- Implement `await_approval` state handling
- Update Slack message to include approval buttons
- Handle approval button clicks in handlers.py
- Implement `handle_approval()` in AgentService

**Step 11: Add Execute Node**
- Implement `execute_node` in nodes.py
- Add `write_to_file` tool
- Test plan → approve → execute flow

### Phase 3: Enhanced Tools (Future)

- Add `execute_command` tool with output streaming
- Add `list_code_definitions` using tree-sitter
- Add git integration (commit, branch, PR)
- Add dashboard visibility for conversations

### Cleanup Tasks (Can be done anytime after MVP)

- Remove `backend/modules/execution_engine/` directory
- Remove `backend/modules/orchestrator/` directory
- Remove `backend/models/run.py`
- Update docker-compose.yml to remove Node.js
- Update documentation
