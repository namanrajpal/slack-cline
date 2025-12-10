# Sline Architecture: Native LangGraph Agent

## Executive Summary

Sline is a **conversational AI coding teammate** that lives in Slack, built with a native Python LangGraph agent architecture. Users interact with Sline through natural @mentions, and the system maintains conversation state across multi-turn discussions.

## Core Design Philosophy

**Sline isn't a bot you command - it's a teammate you collaborate with.**

- **Conversational, not transactional**: Natural @mentions instead of slash commands
- **Thread-based conversations**: Each Slack thread is a persistent conversation
- **Autonomous tool usage**: ReAct agent decides when to read files, search code, etc.
- **State persistence**: Conversations survive server restarts via PostgreSQL

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Slack Workspace                          │
│                                                              │
│  #frontend-team                                             │
│  👤 Alice: @sline what files are in this project?          │
│  🤖 Sline: Hey! 📁 Looking at the codebase...               │
│           (uses list_files tool autonomously)               │
└──────────────────┬──────────────────────────────────────────┘
                   │ Slack Event API
                   │ @mentions trigger webhooks
                   ↓
┌─────────────────────────────────────────────────────────────┐
│              Backend (FastAPI + LangGraph)                  │
│                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐ │
│  │   Slack     │───→│  AgentService │───→│  SlineBrain   │ │
│  │   Gateway   │    │               │    │  (ReAct Agent)│ │
│  └─────────────┘    └───────┬───────┘    └───────┬───────┘ │
│                             │                     │         │
│                             ↓                     ↓         │
│                    ┌─────────────────┐   ┌─────────────┐   │
│                    │ ConversationModel│  │   Tools     │   │
│                    │  (State JSON)    │   │  Bound to   │   │
│                    │                  │   │  Workspace  │   │
│                    └─────────────────┘   └─────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
                  ┌─────────────┐
                  │ PostgreSQL  │
                  │  Database   │
                  └─────────────┘
```

## Component Deep Dive

### 1. Slack Integration Layer

**Primary Interaction**: Event API for @mentions
```python
# handler in modules/slack_gateway/handlers.py
@mentions detected in:
- Top-level messages → Creates new conversation (thread_ts = message_ts)
- Thread replies → Continues existing conversation (thread_ts = existing)

Flow:
1. Slack sends event webhook
2. Extract (channel_id, thread_ts, user_id, text)
3. Strip @sline mention from text
4. Queue background task
5. Acknowledge within 3 seconds
```

**Secondary Interaction**: Slash commands (utilities only)
- `/cline help` - Show interaction help
- `/cline status` - Show active conversations
- Unknown commands suggest using @mentions

### 2. Conversation Model

**One Conversation = One Slack Thread**

```python
# models/conversation.py
class ConversationModel(Base):
    id: UUID
    channel_id: str       # Slack channel
    thread_ts: str        # Thread timestamp (conversation ID)
    project_id: UUID      # Which project/repo
    state_json: JSON      # Serialized SlineState
    message_count: int    # Number of messages exchanged
    
    # Unique constraint on (channel_id, thread_ts)
```

**SlineState** (LangGraph TypedDict):
```python
{
    "messages": [HumanMessage(...), AIMessage(...)],  # Full history
    "workspace_path": "/data/workspaces/<project-id>",
    "project_id": "<uuid>",
    "channel_id": "C123...",
    "thread_ts": "1234567890.123456",
    "user_id": "U123...",
    "mode": "chat",  # chat|planning|awaiting_approval|executing
    "plan": None,    # Set when in planning mode
    "files_context": {}  # Cache of recently read files
}
```

### 3. SlineBrain (The Agent)

**Created per conversation** using LangGraph's `create_react_agent()`:

```python
# modules/agent/brain.py
def create_sline_brain(workspace_path: str):
    model = get_llm_model()  # Claude, GPT-4, etc.
    tools = make_bound_tools(workspace_path)  # Bound tools
    
    return create_react_agent(
        model=model,
        tools=tools,
    )
```

**Key Design Decision**: Tools are **bound** to workspace_path
```python
# LLM only sees:
read_file(path="src/main.py")

# NOT:
read_file(workspace_path="/data/workspaces/...", path="src/main.py")
```

**ReAct Pattern**: Agent autonomously decides when to use tools
```
User: "What files are here?"
→ Agent thinks: "I should use list_files"
→ Agent calls: list_files(path=".", recursive=False)
→ Agent sees: ["README.md", "src/", "tests/"]
→ Agent responds: "This project has a README, src directory, and tests!"
```

### 4. Agent Workflow (LangGraph)

**MVP Graph** (Simple chat-only):
```
START → chat_node → END
```

**Phase 2 Graph** (With planning):
```
START → chat_node ──┬──→ END
                    │
         (user says │
          "create  │
           plan")  │
                    │
                    └──→ plan_node → await_approval → execute_node → chat_node
```

**Nodes**:
- `chat_node`: Handles questions, explanations, tool usage
- `plan_node`: Creates implementation plans (Phase 2)
- `execute_node`: Executes approved plans with write tools (Phase 2)

### 5. Tool Architecture

**Read-Only Tools** (MVP):
```python
# modules/agent/tools/factory.py
def make_bound_tools(workspace_path: str) -> list:
    @tool
    def read_file(path: str) -> str:
        abs_path = os.path.join(workspace_path, path)  # Bound!
        return open(abs_path).read()
    
    @tool
    def list_files(path: str = ".", recursive: bool = False) -> str:
        abs_path = os.path.join(workspace_path, path)
        return "\n".join(os.listdir(abs_path))
    
    @tool
    def search_files(regex: str, path: str = ".", file_pattern: str = "*") -> str:
        # Search files matching pattern
        return results
    
    return [read_file, list_files, search_files]
```

**Write Tools** (Phase 2):
- `write_to_file` - Create/modify files
- `execute_command` - Run shell commands (with approval)

### 6. State Management

**Conversation Lifecycle**:
```
1. User posts: "@sline hello"
   ├─ Check database for conversation(channel_id, message_ts)
   ├─ Not found → Create new ConversationModel
   └─ Initial SlineState with empty messages

2. AgentService processes message
   ├─ Load state from DB (or create initial)
   ├─ Append HumanMessage("hello")
   ├─ Invoke LangGraph
   ├─ Append AIMessage(response)
   └─ Save updated state to DB

3. User replies in thread: "@sline what about X?"
   ├─ Load conversation(channel_id, thread_ts) from DB
   ├─ Deserialize state_json → SlineState with full history
   ├─ Append new HumanMessage
   ├─ Invoke LangGraph (sees all previous messages!)
   └─ Save updated state
```

**Persistence Strategy**:
- In-memory cache for active conversations (performance)
- PostgreSQL for durability (survives restarts)
- state_json stores serialized SlineState

### 7. Project Classification

**Multi-Project Support** via LLM classification:

```python
# modules/agent/classifier.py
async def classify_project(user_question, projects, llm_model):
    # LLM examines user's question and project descriptions
    # Returns: ProjectModel most relevant to the question
    
    # Example:
    # User: "Fix the auth bug"
    # Projects: [frontend-app, backend-api, mobile-app]
    # LLM selects: backend-api (based on "auth" keyword)
```

**For MVP**: Uses first project by default (simplified)

## Data Storage

### Database Schema

**conversations** table:
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    channel_id VARCHAR(255) NOT NULL,
    thread_ts VARCHAR(255) NOT NULL,
    project_id UUID REFERENCES projects(id),
    state_json JSON NOT NULL,  -- Serialized SlineState
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_user_id VARCHAR(255),
    message_count INTEGER,
    UNIQUE(channel_id, thread_ts)
);
```

**projects** table:
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255),
    name VARCHAR(255) UNIQUE,  -- For LLM classification
    description VARCHAR(1024), -- Helps LLM choose project
    slack_channel_id VARCHAR(255),  -- Optional (legacy)
    repo_url VARCHAR(512) NOT NULL,
    default_ref VARCHAR(255) DEFAULT 'main',
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### File Storage

**Workspaces** (cloned repositories):
```
/data/workspaces/
├── <project-uuid-1>/
│   └── (cloned repo contents)
└── <project-uuid-2>/
    └── (cloned repo contents)
```

**Mounted as Docker volume**:
```yaml
# docker-compose.yml
volumes:
  - ./data:/data  # Persists across restarts
```

## Request Flow Example

**User**: `@sline list files in this project`

```
1. Slack Event API → POST /slack/events
   {
     "event": {
       "type": "message",
       "channel": "C0A0B5H7RC3",
       "user": "U0A023XQNVD",
       "text": "<@U_BOT_ID> list files in this project",
       "ts": "1765353374.822169"
     }
   }

2. Backend acknowledges (< 3 seconds) → 200 OK

3. Background task processes:
   ├─ Strip @mention: "list files in this project"
   ├─ Conversation key: "C0A0B5H7RC3:1765353374.822169"
   ├─ Check DB → Not found (new conversation)
   ├─ Classify project → "Slack-Sline" selected
   ├─ Create workspace: /data/workspaces/e1f07d7e-...
   └─ Create ConversationModel in DB

4. Create SlineState:
   {
     "messages": [HumanMessage("list files in this project")],
     "workspace_path": "/data/workspaces/e1f07d7e-...",
     "mode": "chat",
     ...
   }

5. Invoke LangGraph:
   ├─ chat_node called
   ├─ SlineBrain created with bound tools
   ├─ System prompt injected (defines Sline's personality)
   └─ LLM API call to Claude/GPT

6. ReAct Agent decides to use tool:
   ├─ list_files(path=".", recursive=False)
   └─ Gets: ["README.md"]

7. Agent responds:
   "This project has just a README.md file. Would you like me to read it?"

8. Save updated state:
   ├─ Append AIMessage to state.messages
   ├─ Serialize to JSON
   └─ Update ConversationModel.state_json

9. Post to Slack:
   ├─ slack_client.post_message(
   │     channel="C0A0B5H7RC3",
   │     text="This project has just...",
   │     thread_ts="1765353374.822169"
   │   )
   └─ Creates thread in Slack!

10. User sees response in thread
```

**Next reply in thread**:
- Loads conversation from DB with full history ✅
- Agent sees all previous messages ✅
- Continues naturally ✅

## Technology Stack

### Backend
- **Framework**: FastAPI (async Python)
- **Database**: PostgreSQL with SQLAlchemy async
- **Agent**: LangGraph + LangChain
- **LLM Providers**: Anthropic, OpenAI, OpenRouter, etc.
- **Logging**: Structlog (structured JSON logs)

### Frontend (Dashboard)
- **Framework**: React + Vite
- **Styling**: Tailwind CSS
- **State**: React hooks
- **API**: Axios client

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Data Persistence**: Docker volumes (`./data:/data`)
- **Networking**: Docker bridge network

## Key Files

### Agent Module (Core)
```
backend/modules/agent/
├── service.py      # Main interface, conversation management
├── brain.py        # SlineBrain creation, LLM model setup
├── graph.py        # LangGraph workflow definition
├── nodes.py        # Workflow nodes (chat, plan, execute)
├── state.py        # SlineState TypedDict
├── prompts.py      # System prompts and personality
├── classifier.py   # Project classification logic
└── tools/
    └── factory.py  # Tool creation with workspace binding
```

### Slack Integration
```
backend/modules/slack_gateway/
├── handlers.py       # Event webhooks, @mention processing
└── verification.py   # Signature verification
```

### Database Models
```
backend/models/
├── conversation.py   # Conversation state persistence
├── project.py        # Project configurations
└── run.py            # Legacy (to be removed)
```

### Dashboard
```
frontend/src/
├── pages/
│   ├── Dashboard.tsx    # Stats and overview
│   ├── Projects.tsx     # Project management
│   ├── AdminPanel.tsx   # Testing interface
│   └── Settings.tsx     # API configuration
└── api/client.ts        # Backend API client
```

## Configuration

### Environment Variables

```bash
# LLM Provider
CLINE_PROVIDER=anthropic  # anthropic|openai-native|openrouter
CLINE_API_KEY=sk-ant-...
CLINE_MODEL_ID=claude-sonnet-4-5-20250929

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SLACK_BOT_USER_ID=U...  # For @mention detection

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/slack_cline

# System
DEBUG=true
LOG_LEVEL=INFO
DEFAULT_TENANT_ID=default
```

## Deployment

### Development
```bash
# Start services
docker-compose up

# Services:
- Backend: http://localhost:8000
- Database: localhost:5432
- Dashboard: http://localhost:3001 (npm run dev)
```

### Production
```bash
# Same Docker image!
# Just different environment variables

# Deploy to:
- AWS ECS / Fargate
- Google Cloud Run
- Azure Container Apps
- Kubernetes cluster

# Requirements:
- Managed PostgreSQL (RDS, Cloud SQL)
- Domain with SSL
- Slack Event Subscriptions configured
```

## Conversation Flow

### New Conversation (Top-Level @mention)

```
1. User posts in channel: "@sline explain how auth works"
   - No thread_ts yet
   - message_ts = "1234567890.123456"

2. Event API webhook received:
   - channel_id = "C123..."
   - thread_ts = None
   - message_ts = "1234567890.123456"

3. Handler determines conversation_thread_ts:
   - Since thread_ts is None, use message_ts
   - conversation_thread_ts = "1234567890.123456"

4. AgentService.handle_message():
   - Lookup conversation(C123..., 1234567890.123456)
   - Not found → Create new
   - Classify project
   - Create workspace
   - Initialize SlineState

5. Invoke LangGraph:
   - chat_node processes message
   - SlineBrain uses tools autonomously
   - Generates response

6. Post to Slack:
   - channel = "C123..."
   - thread_ts = "1234567890.123456"
   - Creates thread reply!

7. Save state:
   - Serialize SlineState
   - Store in ConversationModel
```

### Continuing Conversation (Thread Reply)

```
1. User replies in thread: "@sline can you show me the code?"
   - thread_ts = "1234567890.123456" (original message)
   - message_ts = "1234567891.234567" (new message)

2. Event API webhook:
   - thread_ts is present
   - conversation_thread_ts = thread_ts

3. AgentService.handle_message():
   - Lookup conversation(C123..., 1234567890.123456)
   - Found! → Load state_json
   - Deserialize → SlineState with full message history

4. Append new message:
   - messages: [
       HumanMessage("explain how auth works"),
       AIMessage("Looking at the codebase..."),
       HumanMessage("can you show me the code?")  ← NEW
     ]

5. Invoke LangGraph:
   - Agent sees ENTIRE conversation history
   - Understands context from previous messages
   - Decides to use read_file tool

6. Post response to same thread
   - Conversation continues naturally!

7. Save updated state
```

## System Prompts

**Sline's Personality** (from `prompts.py`):

```
You are Sline, a friendly AI coding teammate that lives in Slack.

## Your Identity
- Always refer to yourself as "Sline"
- You're a helpful teammate, not a bot
- Be conversational but concise (Slack favors brevity)

## Your Capabilities
- Read files from the codebase
- Search for patterns across files
- List directory contents

## Current Mode: Chat
Answer questions thoroughly but concisely.
Use tools to look up code when needed.
```

**Mode-Specific Instructions**:
- **Chat**: Answer questions, use tools to verify
- **Planning**: Create detailed implementation plans (Phase 2)
- **Executing**: Execute approved plans with write tools (Phase 2)

## Logging

**Clean, structured logs** showing agent activity:

```
2025-12-10T08:12:57.74Z [info] Slack mention_received [slack]
  channel_id=C0A0B5H7RC3
  is_new_conversation=True
  text=Hello, What can you do?

2025-12-10T08:12:59.63Z [info] AgentService initialized
  workspace_base=/data/workspaces

2025-12-10T08:12:59.80Z [info] Selected project 'Slack-Sline'

2025-12-10T08:12:59.82Z [info] chat_node invoked

2025-12-10T08:13:05.11Z [info] 🔧 Tool call: list_files(path='.', recursive=False)

2025-12-10T08:13:05.12Z [info] ✅ Agent made 1 tool call(s)

2025-12-10T08:13:07.51Z [info] 💬 Agent response: Hey there! 👋...

2025-12-10T08:13:07.52Z [info] Created new conversation in database

2025-12-10T08:13:07.84Z [info] Slack message_posted
```

HTTP library verbosity suppressed for clarity.

## Benefits of This Architecture

### vs. Cline CLI Subprocess
✅ **No subprocess complexity** - Direct Python implementation  
✅ **Full control over UX** - Custom conversation flow  
✅ **Simpler state management** - LangGraph handles it  
✅ **No CLI dependency** - Pure Python stack  
✅ **Better error handling** - No parsing subprocess output  

### vs. Direct gRPC
✅ **No proto compilation** - No build complexity  
✅ **Same tools as Cline** - But in native Python  
✅ **Easier testing** - Mock tools, test nodes independently  
✅ **Flexible deployment** - Standard Python container  

## Future Enhancements (Roadmap)

### Phase 2: Planning & Execution
- Add `plan_node` for implementation planning
- Add `execute_node` with write tools
- Slack buttons for plan approval
- Show step-by-step progress

### Phase 3: Advanced Tools
- `list_code_definitions` using tree-sitter
- `execute_command` with streaming output
- Git operations (commit, branch, PR)
- Multi-file edits with diffs

### Phase 4: Repository Management
- Actual git cloning (currently placeholders)
- Workspace caching and cleanup
- Branch switching
- Pull latest changes

### Phase 5: Team Features
- Multi-user conversations (Bob and Alice both @mention Sline)
- Approval from specific users
- Team consensus before execution
- Dashboard analytics (token usage, popular tasks)

## Summary

**Current State** (MVP):
- ✅ @mention-based conversational interaction
- ✅ Thread-based conversation persistence
- ✅ ReAct agent with autonomous tool usage
- ✅ Read-only tools (read_file, list_files, search_files)
- ✅ Multi-turn conversations with memory
- ✅ Dashboard for testing and configuration
- ✅ Clean, structured logging
- ✅ Production-ready architecture

**Architecture Principles**:
- Conversational over transactional
- State persistence via PostgreSQL
- Tools bound to workspace (clean LLM interface)
- Dashboard as development/debugging tool
- Slack as production interface

The system is ready for Phase 2: Planning & Execution! 🚀
