# Cline Core Integration Guide

This document explains how slack-cline integrates with Cline Core via gRPC.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Slack Workspace                          │
│  (Users issue /cline run commands)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP Webhooks
                       ├→ /slack/events
                       └→ /slack/interactivity
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              slack-cline Backend (FastAPI/Python)           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Slack Gateway → Run Orchestrator → Execution Engine │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓ gRPC Client                      │
└──────────────────────────┼──────────────────────────────────┘
                           │ gRPC (port 50051)
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              Cline Core (Node.js gRPC Server)               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  TaskService, StateService, UiService, etc.          │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│              Actual Cline AI Agent Logic                    │
│      (File operations, commands, browser, etc.)             │
└─────────────────────────────────────────────────────────────┘
```

## What is Cline Core?

**Cline Core** is a standalone gRPC server that:
- Runs the actual Cline AI agent logic
- Manages task execution, file operations, command execution
- Exposes gRPC services for clients to interact with
- Is shared by multiple clients (CLI, VSCode extension, and now slack-cline)

## Cline Core gRPC Services

### 1. TaskService (task.proto)
- `newTask()` - Create new task with prompt, files, images, settings
- `cancelTask()` - Cancel current task
- `showTaskWithId()` - Resume existing task by ID
- `askResponse()` - Send followup messages/approvals

### 2. StateService (state.proto)
- `getLatestState()` - Get current state snapshot (JSON)
- `subscribeToState()` - Stream state updates
- `togglePlanActModeProto()` - Switch between plan/act modes
- `updateTaskSettings()` - Update task-specific settings

### 3. UiService (ui.proto)
- `subscribeToPartialMessage()` - Stream partial/streaming assistant messages

### 4. CheckpointsService (checkpoints.proto)
- `checkpointRestore()` - Restore task to checkpoint

## How slack-cline Integrates

### 1. Connection Setup

The `ExecutionEngineClient` in `backend/modules/execution_engine/client.py` creates a gRPC channel to Cline Core:

```python
self.channel = grpc.insecure_channel(f"{host}:{port}")  # Default: localhost:50051
self.task_stub = task_pb2_grpc.TaskServiceStub(self.channel)
self.state_stub = state_pb2_grpc.StateServiceStub(self.channel)
self.ui_stub = ui_pb2_grpc.UiServiceStub(self.channel)
```

### 2. Task Creation Flow

When a user runs `/cline run <task>` in Slack:

```
1. Slack → slack-cline: HTTP POST /slack/events
2. Slack Gateway: Parse command → StartRunCommand
3. Run Orchestrator: Create DB record, call Execution Engine
4. Execution Engine: gRPC call to Cline Core TaskService.newTask()
   - Request: NewTaskRequest(text=prompt, images=[], files=[], task_settings=None)
   - Response: Task ID
5. Execution Engine: Subscribe to StateService.subscribeToState()
   - Stream state updates (messages, events, status changes)
6. Run Orchestrator: Process events, update DB, post to Slack
```

### 3. State-Based Message Model

Cline uses a **state-based architecture**:

- All conversation history is in the `state_json` field
- State updates contain the complete conversation history
- Messages are extracted from state JSON by parsing the `clineMessages` array

```python
# Example state structure
{
  "version": 7,
  "mode": "plan",  # or "act"
  "currentTaskItem": { "id": "task_123", ... },
  "clineMessages": [
    { "ts": 123456, "type": "say", "say": "text", "text": "Hello", "partial": false },
    { "ts": 123457, "type": "ask", "ask": "command", "text": "npm test", "partial": false }
  ],
  ...
}
```

### 4. Event Streaming

The execution engine subscribes to two streams:

**State Stream** (for complete messages):
```python
for state in state_stub.SubscribeToState():
    messages = extract_messages_from_state(state.state_json)
    for msg in messages:
        if msg.type == "ask" and msg.ask == "command":
            # User needs to approve command
        elif msg.type == "say" and msg.say == "completion_result":
            # Task completed
```

**Partial Message Stream** (for streaming text):
```python
for partial_msg in ui_stub.SubscribeToPartialMessage():
    # Real-time streaming of assistant responses
    display_streaming_text(partial_msg)
```

## Running Cline Core

### Option 1: Use the Cline CLI (Easiest)

The Cline CLI automatically manages Cline Core instances:

```bash
# Install Cline CLI
npm install -g cline

# Start a Cline instance (automatically starts Cline Core at port 50051)
cline

# The CLI manages the instance lifecycle
```

### Option 2: Run Cline Core Standalone

```bash
cd cline

# Compile standalone build
npm run compile-standalone

# Run Cline Core server
node dist-standalone/cline-core.js --port 50051

# Or use the helper script
./scripts/runclinecore.sh
```

### Option 3: Programmatic Instance Management

Use the SQLite-based instance registry (how the CLI does it):

```python
from cline.cli.pkg.cli.sqlite import InstanceRegistry

registry = InstanceRegistry()
instance = registry.start_new_instance()
# instance.address = "localhost:50051"
```

## Development Setup

### 1. Compile Proto Files

```bash
cd slack-cline/backend
python compile_protos.py
```

This generates:
- `proto/cline/task_pb2.py` - Message classes
- `proto/cline/task_pb2_grpc.py` - Service stubs
- Similar files for state, ui, common, checkpoints

### 2. Start Cline Core

```bash
# Terminal 1: Start Cline Core
cd cline
npm run compile-standalone
node dist-standalone/cline-core.js
```

### 3. Start slack-cline Backend

```bash
# Terminal 2: Start backend
cd slack-cline
docker-compose up backend
```

### 4. Configure Connection

In `.env`:
```bash
CLINE_CORE_HOST=localhost  # or host.docker.internal if in Docker
CLINE_CORE_PORT=50051
```

## Testing the Integration

### 1. Test gRPC Connection

```python
from modules.execution_engine.client import ExecutionEngineClient

client = ExecutionEngineClient(host="localhost", port=50051)
await client.connect()
# Should connect successfully
```

### 2. Test Task Creation

```python
task_id = await client.start_run(
    repo_url="https://github.com/example/repo.git",
    ref="main",
    prompt="Create a hello world script"
)
print(f"Created task: {task_id}")
```

### 3. Test Event Streaming

```python
async for event in client.stream_events(task_id):
    print(f"Event: {event.event_type} - {event.message}")
```

## Common Issues

### Connection Refused
**Problem**: `grpc._channel._InactiveRpcError: <_InactiveRpcError of RPC that terminated with: status = UNAVAILABLE`

**Solution**: Ensure Cline Core is running:
```bash
# Check if Cline Core is running
lsof -i :50051  # macOS/Linux
netstat -ano | findstr :50051  # Windows
```

### Docker Network Issues
**Problem**: Backend can't reach Cline Core from Docker

**Solution**: Use `host.docker.internal` instead of `localhost`:
```bash
CLINE_CORE_HOST=host.docker.internal  # For Docker on Mac/Windows
CLINE_CORE_HOST=172.17.0.1  # For Docker on Linux
```

### Proto Import Errors
**Problem**: `ImportError: cannot import name 'task_pb2'`

**Solution**: Compile protos first:
```bash
cd slack-cline/backend
python compile_protos.py
```

### State JSON Parsing Errors
**Problem**: Can't extract messages from state

**Solution**: State structure changed - check `clineMessages` array in state JSON

## Production Deployment

### 1. Cline Core as Sidecar

Deploy Cline Core alongside backend in same pod/container group:

```yaml
# Kubernetes example
spec:
  containers:
  - name: backend
    image: slack-cline-backend
  - name: cline-core
    image: cline-core
    ports:
    - containerPort: 50051
```

### 2. Cline Core as Separate Service

Deploy as independent service with internal load balancer:

```yaml
# docker-compose
services:
  cline-core:
    image: cline-core
    networks:
      - internal
  backend:
    depends_on:
      - cline-core
    environment:
      - CLINE_CORE_HOST=cline-core
```

### 3. Connection Pooling

For production, implement connection pooling:

```python
from grpc import aio

class ExecutionEngineClient:
    def __init__(self):
        self.channel_pool = aio.insecure_channel(
            target,
            options=[
                ('grpc.max_connection_idle_ms', 60000),
                ('grpc.keepalive_time_ms', 30000),
            ]
        )
```

## Reference

- **Cline CLI Source**: `cline/cli/pkg/cli/task/manager.go`
- **Proto Definitions**: `cline/proto/cline/*.proto`
- **Standalone Core**: `cline/src/standalone/cline-core.ts`
- **Instance Management**: `cline/cli/pkg/cli/sqlite/registry.go`

## Next Steps

1. Run `python backend/compile_protos.py` to generate gRPC code
2. Start Cline Core: `node cline/dist-standalone/cline-core.js`
3. Test connection from slack-cline backend
4. Monitor logs to verify task creation and event streaming
