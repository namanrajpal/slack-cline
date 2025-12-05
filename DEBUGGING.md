# Debugging Guide for slack-cline

This guide explains how to debug the Python backend running in Docker using VS Code's debugger.

## Quick Start

### Enable Debugging Mode

1. **Uncomment the debug command** in `docker-compose.yml`:
   ```yaml
   backend:
     # Uncomment this line:
     command: python -m debugpy --listen 0.0.0.0:5678 --wait-for-client main.py
   ```

2. **Rebuild and restart**:
   ```bash
   docker-compose down
   docker-compose build backend
   docker-compose up
   ```

3. **Wait for debugger message**:
   ```
   backend-1  | Waiting for debugger to attach...
   ```

4. **Attach VS Code debugger**:
   - Press `F5` or go to Run & Debug panel
   - Select "Python: Attach to Docker"
   - Click ▶️ Start Debugging

5. **Set breakpoints** and trigger requests via Admin Panel!

---

## Detailed Setup

### Prerequisites

- VS Code with Python extension installed
- Docker Desktop running
- slack-cline backend container running

### Step 1: Dependencies Already Added ✅

The setup is already complete:
- ✅ `debugpy` added to `requirements.txt`
- ✅ Port 5678 exposed in `docker-compose.yml`
- ✅ Launch configuration created in `.vscode/launch.json`

### Step 2: Enable Debug Mode

Edit `docker-compose.yml` and **uncomment** the debug command:

```yaml
backend:
  ports:
    - "8000:8000"
    - "5678:5678"  # Already added
  # Uncomment this line to enable debugging:
  command: python -m debugpy --listen 0.0.0.0:5678 --wait-for-client main.py
```

**Options**:
- `--wait-for-client`: Waits for debugger before starting (recommended)
- Without `--wait-for-client`: Starts immediately, attach anytime

### Step 3: Rebuild Container

```bash
# Stop services
docker-compose down

# Rebuild to include debugpy
docker-compose build backend

# Start with debug enabled
docker-compose up
```

### Step 4: Attach Debugger

**In VS Code**:
1. Open the `slack-cline` folder
2. Press `F5` or click Run & Debug (Ctrl+Shift+D)
3. Select "Python: Attach to Docker" from dropdown
4. Click ▶️ or press `F5`

You should see:
```
✅ Debugger attached
✅ Status bar shows "Attached to localhost:5678"
✅ Backend starts processing requests
```

---

## Setting Breakpoints

### Key Files to Debug

#### 1. Slack Command Reception
**File**: `backend/modules/slack_gateway/handlers.py`

```python
# Line ~105 - When slash command is received
async def handle_run_command(command_data: SlackCommandSchema, task_prompt: str):
    # Set breakpoint here
    if not task_prompt.strip():
        ...
```

#### 2. Run Orchestration
**File**: `backend/modules/orchestrator/service.py`

```python
# Line ~40 - When run starts
async def start_run(self, command: StartRunCommand, session: AsyncSession):
    # Set breakpoint here
    log_run_event("start_requested", ...)
```

```python
# Line ~65 - Before calling Cline CLI
result = await self.cli_client.start_run(
    # Set breakpoint here
    repo_url=project.repo_url,
    ...
)
```

#### 3. Cline CLI Execution
**File**: `backend/modules/execution_engine/cli_client.py`

```python
# Line ~45 - Start of run execution
async def start_run(self, repo_url: str, ...):
    # Set breakpoint here
    start_time = datetime.utcnow()
```

```python
# Line ~70 - Repository cloning
workspace_path = await self._clone_repository(repo_url, ref)
# Set breakpoint here
```

```python
# Line ~75 - Instance creation
instance_address = await self._create_instance(workspace_path)
# Set breakpoint here
```

```python
# Line ~80 - Authentication
await self._configure_auth(instance_address, workspace_path, ...)
# Set breakpoint here
```

```python
# Line ~90 - Task creation
task_id = await self._create_task(instance_address, workspace_path, prompt)
# Set breakpoint here
```

#### 4. Event Streaming
**File**: `backend/modules/execution_engine/cli_client.py`

```python
# Line ~120 - Event streaming
async def stream_events(self, instance_address: str, ...):
    # Set breakpoint here
    async for line in process.stdout:
        ...
```

---

## Debugging Workflow

### Scenario 1: Debug Admin Panel Test

1. **Set breakpoints** in dashboard routes:
   ```python
   # backend/modules/dashboard/routes.py:280
   async def test_slack_command(request: TestSlackCommandSchema):
       # Breakpoint here
   ```

2. **Start debugger** (F5)

3. **Trigger request** from Admin Panel

4. **Step through code**:
   - F10: Step Over
   - F11: Step Into
   - Shift+F11: Step Out
   - F5: Continue

5. **Inspect variables**:
   - Hover over variables
   - Use Debug Console to evaluate expressions
   - Check Variables panel

### Scenario 2: Debug Cline CLI Execution

1. **Set breakpoints** in CLI client:
   ```python
   # backend/modules/execution_engine/cli_client.py
   # Lines: 45, 70, 75, 80, 90, 120
   ```

2. **Start debugger**

3. **Trigger run** via Admin Panel

4. **Inspect**:
   - `repo_url` - Repository being cloned
   - `workspace_path` - Where it's cloning to
   - `instance_address` - Cline instance location
   - `task_id` - Created task ID
   - `cmd` - Actual CLI command being executed

5. **Check subprocess output**:
   ```python
   # In debug console
   print(stdout.decode('utf-8'))
   print(stderr.decode('utf-8'))
   ```

### Scenario 3: Debug Database Operations

1. **Set breakpoints** in service:
   ```python
   # backend/modules/orchestrator/service.py:~60
   run = RunModel(...)
   session.add(run)
   # Breakpoint here
   await session.commit()
   ```

2. **Inspect database objects**:
   ```python
   # In debug console
   print(f"Run ID: {run.id}")
   print(f"Status: {run.status}")
   print(f"Cline ID: {run.cline_run_id}")
   ```

3. **Check database** in parallel terminal:
   ```bash
   docker-compose exec db psql -U postgres -d slack_cline \
     -c "SELECT * FROM runs ORDER BY created_at DESC LIMIT 1;"
   ```

---

## Debug Console Commands

While paused at a breakpoint, use the Debug Console:

### Inspect Variables
```python
# Print complex objects
print(f"Project: {project.__dict__}")
print(f"Run: {run.__dict__}")

# Check type
type(result)

# Evaluate expressions
len(projects)
result.get("instance_address")
```

### Execute Queries
```python
# Import database utilities
from database import get_session
from models.run import RunModel

# Query data
import asyncio
async for session in get_session():
    runs = await session.execute("SELECT * FROM runs")
    for r in runs:
        print(r)
```

### Check Environment
```python
import os
print(f"API Key: {os.getenv('CLINE_API_KEY')[:10]}...")
print(f"Provider: {os.getenv('CLINE_PROVIDER')}")
```

---

## Common Debugging Scenarios

### Debug "Run Failed to Start"

**Set breakpoints**:
1. `orchestrator/service.py:start_run()` - Line ~40
2. `cli_client.py:start_run()` - Line ~45
3. `cli_client.py:_clone_repository()` - Line ~180
4. `cli_client.py:_create_instance()` - Line ~200

**Inspect**:
- Check `repo_url` is valid
- Check `workspace_path` creation
- Check subprocess `returncode`
- Check `stderr` for error messages

### Debug "Authentication Failed"

**Set breakpoints**:
1. `cli_client.py:_configure_auth()` - Line ~240

**Inspect**:
- `provider` - Should match your LLM provider
- `api_key` - Check it's not empty (careful logging!)
- `model_id` - Verify format
- `cmd` - The actual command being run
- `process.returncode` - Exit code
- `stderr.decode('utf-8')` - Error output

### Debug "Event Stream Issues"

**Set breakpoints**:
1. `cli_client.py:stream_events()` - Line ~120
2. `orchestrator/service.py:_process_run_event()` - Line ~180

**Inspect**:
- `line` - Current output line
- `event.event_type` - What type of event
- `run.status` - Current status

---

## Debugging Tips

### 1. Conditional Breakpoints

Right-click breakpoint → Edit Breakpoint → Add condition:

```python
# Only break for specific channel
channel_id == "C12345678"

# Only break for failed runs
run.status == RunStatus.FAILED

# Only break when error occurs
"error" in str(e).lower()
```

### 2. Logpoints

Instead of breakpoints, add logpoints (right-click line number):

```python
# Log without stopping
f"Processing run {run.id} with status {run.status}"
```

### 3. Watch Expressions

Add to Watch panel:
- `run.status.value`
- `len(self._active_streams)`
- `result["workspace_path"]`
- `process.returncode`

### 4. Call Stack Analysis

When paused, check Call Stack panel to understand:
- How you got to this point
- Which function called which
- Async task hierarchy

---

## Performance Debugging

### Check Slow Operations

1. **Set breakpoint before slow operation**
2. **Note timestamp** in debug console:
   ```python
   from datetime import datetime
   start = datetime.utcnow()
   ```
3. **Continue** (F5)
4. **Set breakpoint after** operation
5. **Calculate duration**:
   ```python
   duration = (datetime.utcnow() - start).total_seconds()
   print(f"Operation took {duration}s")
   ```

### Profile Async Operations

```python
# In debug console
import asyncio
tasks = asyncio.all_tasks()
print(f"Active tasks: {len(tasks)}")
for task in tasks:
    print(f"  {task.get_name()}: {task}")
```

---

## Troubleshooting Debugger

### "Cannot connect to debugger"

**Solutions**:
1. Check port 5678 is exposed: `docker-compose ps`
2. Verify debugpy is installed: `docker-compose exec backend pip list | grep debugpy`
3. Check backend is waiting: Look for "Waiting for debugger..." in logs
4. Rebuild container: `docker-compose build backend`

### "Breakpoints not hitting"

**Solutions**:
1. Check path mappings in launch.json are correct
2. Verify you're editing `backend/` files (not `/app/` in container)
3. Make sure file is actually being executed (check call stack)
4. Try adding a `print()` statement to verify file is loaded

### "Variables show <optimized out>"

**Solutions**:
1. Set `"justMyCode": false` in launch.json (already done)
2. Try inspecting in debug console instead of hover
3. Add to Watch panel for persistent viewing

### Backend not starting

**Check**:
1. `docker-compose logs backend` for errors
2. Syntax errors in Python files
3. Missing dependencies
4. Port conflicts (5678 already in use)

---

## Development Modes

### Mode 1: Normal (No Debug)

```yaml
# docker-compose.yml
# Command line commented out
# command: python -m debugpy --listen 0.0.0.0:5678 --wait-for-client main.py

# Backend starts immediately
docker-compose up
```

**Use when**: Regular development, no breakpoints needed

### Mode 2: Debug with Wait

```yaml
# docker-compose.yml
command: python -m debugpy --listen 0.0.0.0:5678 --wait-for-client main.py

# Backend waits for debugger
docker-compose up
# Then attach debugger (F5)
```

**Use when**: Want to debug startup code, initial requests

### Mode 3: Debug without Wait

```yaml
# docker-compose.yml
command: python -m debugpy --listen 0.0.0.0:5678 main.py

# Backend starts immediately, attach anytime
docker-compose up
# Attach debugger when needed
```

**Use when**: Want to attach/detach during development

---

## Example Debugging Session

### Scenario: Debug Failed Cline Run

**Goal**: Understand why a Cline run failed

**Steps**:

1. **Enable debug mode**:
   ```bash
   # Uncomment debug command in docker-compose.yml
   docker-compose down
   docker-compose up
   ```

2. **Attach debugger** (F5)

3. **Set breakpoints**:
   ```python
   # cli_client.py:start_run() - Line ~45
   # cli_client.py:_create_instance() - Line ~200
   # cli_client.py:_create_task() - Line ~280
   ```

4. **Trigger run** via Admin Panel:
   - Channel: C_TEST_CHANNEL
   - Task: "create a README"

5. **Step through execution**:
   - **Breakpoint 1**: Check `repo_url`, `ref`, `prompt`
   - **Step Into** `_clone_repository()`
   - Check `workspace_path` is created
   - **Step Into** `_create_instance()`
   - Check `instance_address` returned
   - **Step Into** `_configure_auth()`
   - **Inspect** `cmd` array - is it correct?
   - Check `process.returncode` - is it 0?
   - If error, check `stderr.decode('utf-8')`

6. **Fix issue** based on findings

7. **Restart** and test again

---

## Breakpoint Locations Reference

### Request Flow

```python
# 1. API Request Received
backend/modules/dashboard/routes.py:test_slack_command()  # Line ~265

# 2. Slack Handler Called
backend/modules/slack_gateway/handlers.py:handle_cline_command()  # Line ~110
backend/modules/slack_gateway/handlers.py:handle_run_command()  # Line ~145

# 3. Run Orchestration
backend/modules/orchestrator/service.py:start_run()  # Line ~40
backend/modules/orchestrator/service.py:_resolve_project()  # Line ~130

# 4. CLI Client Execution
backend/modules/execution_engine/cli_client.py:start_run()  # Line ~45
backend/modules/execution_engine/cli_client.py:_clone_repository()  # Line ~180
backend/modules/execution_engine/cli_client.py:_create_instance()  # Line ~200
backend/modules/execution_engine/cli_client.py:_configure_auth()  # Line ~240
backend/modules/execution_engine/cli_client.py:_create_task()  # Line ~280

# 5. Event Streaming
backend/modules/execution_engine/cli_client.py:stream_events()  # Line ~120
backend/modules/orchestrator/service.py:_handle_event_stream()  # Line ~175
backend/modules/orchestrator/service.py:_process_run_event()  # Line ~200
```

### Database Operations

```python
# Project queries
backend/modules/dashboard/service.py:get_projects()  # Line ~30
backend/modules/dashboard/service.py:create_project()  # Line ~45

# Run queries
backend/modules/dashboard/service.py:get_runs()  # Line ~130
backend/models/run.py:mark_started()  # Line ~80
backend/models/run.py:mark_completed()  # Line ~85
```

---

## Advanced Debugging

### Debug Async Code

When debugging async functions:

```python
# Check current event loop
import asyncio
loop = asyncio.get_event_loop()
print(f"Loop running: {loop.is_running()}")

# Check pending tasks
tasks = asyncio.all_tasks()
print(f"Active tasks: {len(tasks)}")
```

### Debug Subprocess Calls

When debugging CLI subprocess calls:

```python
# Before executing
print(f"Command: {' '.join(cmd)}")
print(f"CWD: {workspace_path}")

# After executing
print(f"Return code: {process.returncode}")
print(f"Stdout: {stdout.decode('utf-8')}")
print(f"Stderr: {stderr.decode('utf-8')}")
```

### Debug JSON Parsing

```python
# Check raw output before parsing
raw_output = stdout.decode('utf-8')
print(f"Raw: {raw_output}")

# Try parsing
import json
try:
    data = json.loads(raw_output)
    print(f"Parsed: {data}")
except json.JSONDecodeError as e:
    print(f"JSON error: {e}")
    print(f"Failed at: {raw_output[max(0, e.pos-20):e.pos+20]}")
```

---

## Debugging vs Logging

### When to Use Debugger

- ✅ Understanding complex code flow
- ✅ Inspecting object state at specific points
- ✅ Stepping through async operations
- ✅ Finding root cause of exceptions
- ✅ Testing hypothesis about behavior

### When to Use Logging

- ✅ Production debugging
- ✅ Long-running operations
- ✅ Multiple request correlation
- ✅ Performance monitoring
- ✅ Audit trails

### Combined Approach

```python
# Add logs for production
logger.info(f"Starting run {run.id}")

# But also set breakpoint for dev debugging
# Breakpoint here (removed in production)
result = await self.cli_client.start_run(...)

logger.info(f"Run started: {result}")
```

---

## Performance Impact

### Debugger Overhead

- **With `--wait-for-client`**: Backend won't start until attached (startup delay)
- **Without wait**: Minimal impact (~1-2% slower)
- **Active debugging**: Paused execution (expected)

### Recommendation

**Development**:
- Use debug mode during active development
- Disable when not debugging for better performance

**Production**:
- Never enable debug mode
- Use logging instead
- Consider APM tools (DataDog, New Relic)

---

## Docker-Specific Tips

### View Container Internals

While debugging, you can inspect the container:

```bash
# Shell into running container
docker-compose exec backend /bin/bash

# Check files
ls -la /app
ls -la /home/app/workspaces

# Check processes
ps aux

# Check environment
env | grep CLINE

# Test Cline CLI manually
cline --version
cline instance list
```

### Hot Reload with Debugger

The volume mount allows hot reload:
1. Edit Python file
2. Debugger detects changes
3. FastAPI auto-reloads
4. Debugger re-attaches automatically

**No rebuild needed** for code changes!

---

## Debugging Checklist

Before starting a debug session:

- [ ] `debugpy` in requirements.txt
- [ ] Port 5678 exposed in docker-compose.yml
- [ ] Debug command uncommented (if using wait mode)
- [ ] Container rebuilt with `docker-compose build backend`
- [ ] VS Code Python extension installed
- [ ] `.vscode/launch.json` exists
- [ ] Backend running (`docker-compose up`)
- [ ] Debugger attached (F5)
- [ ] Breakpoints set in relevant files

---

## Quick Reference

```bash
# Enable debugging
1. Edit docker-compose.yml - uncomment debug command
2. docker-compose down
3. docker-compose build backend
4. docker-compose up

# Attach in VS Code
1. Press F5
2. Select "Python: Attach to Docker"
3. Wait for "Attached" status

# Set breakpoints
1. Open Python file
2. Click left of line number (red dot)
3. Trigger request
4. Debug when paused

# Disable debugging
1. Comment out debug command in docker-compose.yml
2. docker-compose restart backend
```

---

## Next Steps

1. **Try it now**: Enable debug mode and attach
2. **Set first breakpoint**: In `cli_client.py:start_run()`
3. **Trigger test**: Use Admin Panel
4. **Explore**: Step through code, inspect variables
5. **Learn**: Understand the full execution flow

Happy debugging! 🐛🔍
