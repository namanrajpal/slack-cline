# Cline CLI Debugging Guide & Gotchas

This document provides comprehensive guidance on debugging Cline CLI issues within the slack-cline system, common gotchas, and how to verify what Cline is doing.

## Table of Contents

1. [Understanding the Architecture](#understanding-the-architecture)
2. [Verifying Cline CLI Installation](#verifying-cline-cli-installation)
3. [Instance Management](#instance-management)
4. [Task Management](#task-management)
5. [Authentication Debugging](#authentication-debugging)
6. [Common Gotchas](#common-gotchas)
7. [Log Analysis](#log-analysis)
8. [Interactive Debugging](#interactive-debugging)
9. [Troubleshooting Flowchart](#troubleshooting-flowchart)

---

## Understanding the Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Docker Container (backend)                                  │
│                                                             │
│   Python Backend (FastAPI)                                  │
│         │                                                   │
│         ▼ subprocess calls                                  │
│   Cline CLI (npm package - globally installed)              │
│         │                                                   │
│         ▼ manages                                           │
│   Cline Core (Node.js runtime)                              │
│         │                                                   │
│         ▼ gRPC server                                       │
│   Instance (e.g., 127.0.0.1:41987)                          │
│                                                             │
│   /home/app/workspaces/  ◄── Docker volume                  │
│   └── run-20251207-123456/  ◄── Cloned repo workspace       │
└─────────────────────────────────────────────────────────────┘
```

**Key Points:**
- Cline CLI is installed globally via `npm install -g cline`
- Each run creates a new workspace directory
- Instances run as background processes inside the container
- All debugging must be done from within the Docker container

---

## Verifying Cline CLI Installation

### Check CLI Version

```powershell
# From host
docker-compose exec backend cline --version

# Expected output: something like "cline 1.0.0"
```

### Check CLI Location

```powershell
docker-compose exec backend which cline
# Expected: /usr/local/bin/cline or similar
```

### Check Node.js Environment

```powershell
docker-compose exec backend node --version
# Expected: v20.x.x

docker-compose exec backend npm --version
```

### Verify CLI Help

```powershell
docker-compose exec backend cline --help
```

This should show all available commands:
- `instance` - Manage Cline instances
- `task` - Manage tasks
- `auth` - Configure authentication
- `start` - Quick start a task

---

## Instance Management

### List Running Instances

```powershell
docker-compose exec backend cline instance list
```

**Output when instances are running:**
```
Instance ID                              Address          Status
---------------------------------------- ---------------- --------
abc123                                   127.0.0.1:41987  running
def456                                   127.0.0.1:42000  running
```

**Output when no instances:**
```
No running instances found.
```

### Create a New Instance

```powershell
# Interactive mode (will block terminal)
docker-compose exec backend cline instance new

# From a specific directory
docker-compose exec -w /home/app/workspaces/run-test backend cline instance new
```

**Expected output:**
```
Starting new Cline instance...
Successfully started new instance:
Address: 127.0.0.1:41987
```

### Kill an Instance

```powershell
docker-compose exec backend cline instance kill 127.0.0.1:41987
```

### Kill ALL Instances

```powershell
# List and kill all manually
docker-compose exec backend cline instance list
# Then kill each one

# Or restart the container (kills all)
docker-compose restart backend
```

---

## Task Management

### View Current Task

```powershell
# View task on a specific instance
docker-compose exec backend cline task view --address 127.0.0.1:41987
```

### Follow Task Output (Real-time)

```powershell
# Follow until task completes
docker-compose exec backend cline task view --follow-complete --address 127.0.0.1:41987

# Just follow (may not exit automatically)
docker-compose exec backend cline task view --follow --address 127.0.0.1:41987
```

### Create a New Task

```powershell
# YOLO mode (autonomous, no approval needed)
docker-compose exec -w /home/app/workspaces/run-test backend cline task new -y "Create a README file"

# With specific mode
docker-compose exec -w /home/app/workspaces/run-test backend cline task new -y -m act "Create a README file"

# On a specific instance
docker-compose exec backend cline task new -y --address 127.0.0.1:41987 "Create a README file"
```

### Pause/Cancel a Task

```powershell
docker-compose exec backend cline task pause --address 127.0.0.1:41987
```

### Send Response to Task (Approve/Deny)

```powershell
# Approve a pending action
docker-compose exec backend cline task send --approve --address 127.0.0.1:41987

# Deny a pending action
docker-compose exec backend cline task send --deny --address 127.0.0.1:41987

# Send a custom message
docker-compose exec backend cline task send --address 127.0.0.1:41987 "Please proceed with the change"
```

---

## Authentication Debugging

### Configure Authentication

```powershell
# Anthropic
docker-compose exec backend cline auth \
  --provider anthropic \
  --apikey sk-ant-xxxxx \
  --modelid claude-sonnet-4-5-20250929

# OpenAI
docker-compose exec backend cline auth \
  --provider openai-native \
  --apikey sk-xxxxx \
  --modelid gpt-4o

# OpenRouter
docker-compose exec backend cline auth \
  --provider openrouter \
  --apikey sk-or-xxxxx \
  --modelid anthropic/claude-3.5-sonnet
```

### Verify Authentication

After running auth, try creating a simple task:

```powershell
docker-compose exec -w /tmp backend cline task new -y "Say hello"
```

If authentication fails, you'll see errors like:
- `Invalid API key`
- `Model not found`
- `Authentication failed`

### Check Environment Variables

```powershell
docker-compose exec backend env | grep CLINE
```

Expected:
```
CLINE_DIR=/home/app/.cline
CLINE_PROVIDER=anthropic
CLINE_API_KEY=sk-ant-xxxxx
CLINE_MODEL_ID=claude-sonnet-4-5-20250929
```

---

## Common Gotchas

### 1. Instance Process Doesn't Exit

**Problem:** `cline instance new` runs in foreground mode and doesn't exit.

**Solution:** This is expected behavior. The instance needs to stay running. The backend reads the instance address from stdout and continues without waiting for the process to exit.

```python
# Backend waits for "Address: X.X.X.X:PORT" line, then continues
# The instance process continues running in background
```

### 2. Task Stuck Waiting for Approval

**Problem:** Task stops making progress, seems stuck.

**Cause:** Even with `-y` (YOLO) mode, some operations may require approval depending on Cline's configuration.

**Debug:**
```powershell
# Check what the task is waiting for
docker-compose exec backend cline task view --address 127.0.0.1:41987

# Look for "Approve?" or "waiting for" in output
```

**Solution:**
```powershell
# Send approval
docker-compose exec backend cline task send --approve --address 127.0.0.1:41987
```

### 3. "No Instance Found" Errors

**Problem:** Task commands fail with "instance not found" or similar.

**Causes:**
- Instance was killed or crashed
- Container was restarted
- Wrong address used

**Debug:**
```powershell
# List active instances
docker-compose exec backend cline instance list

# Check if instance process is running
docker-compose exec backend ps aux | grep cline
```

### 4. Git Clone Fails

**Problem:** Repository cloning fails during run startup.

**Causes:**
- Invalid repo URL
- Private repo without credentials
- Network issues
- Branch doesn't exist

**Debug:**
```powershell
# Try cloning manually
docker-compose exec backend git clone --depth 1 -b main https://github.com/user/repo.git /tmp/test-clone
```

**Solution for private repos:**
- Configure SSH keys in the container
- Use HTTPS with token: `https://TOKEN@github.com/user/repo.git`

### 5. npm install Fails

**Problem:** Dependency installation fails in workspace.

**Debug:**
```powershell
# Check if npm is available
docker-compose exec backend npm --version

# Try installing manually in workspace
docker-compose exec -w /home/app/workspaces/run-xxx backend npm install
```

**Common issues:**
- Network issues inside Docker
- Missing build tools for native modules
- Node.js version incompatibility

### 6. JSON Parsing Errors

**Problem:** Backend fails to parse CLI output.

**Cause:** CLI output format changed or contains unexpected text.

**Debug:**
```powershell
# Run CLI command with explicit output format
docker-compose exec backend cline instance new --output-format json
docker-compose exec backend cline task new --output-format json -y "test"
```

**Check backend logs for raw output:**
```powershell
docker-compose logs backend | grep "CLI.*output"
```

### 7. Timeout Errors

**Problem:** Operations timeout waiting for CLI response.

**Causes:**
- LLM API slow or rate-limited
- Large codebase analysis
- Complex task

**Backend timeout settings in `cli_client.py`:**
```python
# Current timeout: 30 seconds per line of output
line_bytes = await asyncio.wait_for(
    process.stdout.readline(),
    timeout=30.0
)
```

### 8. Permission Errors

**Problem:** File operations fail with permission denied.

**Cause:** Docker container runs as `app` user, not root.

**Check:**
```powershell
docker-compose exec backend whoami
# Should output: app

docker-compose exec backend ls -la /home/app/workspaces/
```

### 9. Instance Address Mismatch

**Problem:** Backend stores wrong instance address.

**Debug in Python:**
```python
# Add logging to _create_instance method
logger.info(f"Raw CLI output: {full_output}")
logger.info(f"Parsed address: {instance_address}")
```

**Check stored metadata:**
```powershell
# Look at orchestrator metadata in logs
docker-compose logs backend | grep "instance_address"
```

### 10. Workspace Not Cleaned Up

**Problem:** Old workspaces accumulate in `/home/app/workspaces/`.

**Check:**
```powershell
docker-compose exec backend ls -la /home/app/workspaces/
docker-compose exec backend du -sh /home/app/workspaces/*
```

**Manual cleanup:**
```powershell
docker-compose exec backend rm -rf /home/app/workspaces/run-*
```

---

## Log Analysis

### Backend Logs

```powershell
# All backend logs
docker-compose logs -f backend

# Filter for specific components
docker-compose logs backend | grep "\[execution.cli\]"
docker-compose logs backend | grep "\[orchestrator\]"
docker-compose logs backend | grep "\[slack\]"
```

### Log Event Types

| Event Type | Description |
|------------|-------------|
| `cli_run_started` | Cline run began successfully |
| `cli_run_failed` | Cline run failed to start |
| `cli_output` | Line from CLI output stream |
| `event_received` | Event parsed from CLI output |
| `run_created` | Run record created in database |
| `execution_started` | Task execution began |

### Example Log Analysis

```
# Look for run lifecycle
docker-compose logs backend | grep "Run" | grep -E "created|started|completed|failed"

# Check for errors
docker-compose logs backend | grep -i "error\|failed\|exception"

# Check CLI output
docker-compose logs backend | grep "CLI.*output"
```

---

## Interactive Debugging

### Enter the Container

```powershell
# As app user (default)
docker-compose exec backend bash

# As root (for installing tools)
docker-compose exec -u root backend bash
```

### Manual Workflow Test

```bash
# Inside container:

# 1. Create workspace
mkdir -p /home/app/workspaces/debug-test
cd /home/app/workspaces/debug-test

# 2. Clone a test repo
git clone --depth 1 https://github.com/some/repo.git .

# 3. Configure auth
cline auth --provider anthropic --apikey $CLINE_API_KEY --modelid claude-sonnet-4-5-20250929

# 4. Create instance
cline instance new
# Note the address (e.g., 127.0.0.1:41987)

# 5. In another terminal, create task
docker-compose exec backend cline task new -y --address 127.0.0.1:41987 "Create a hello.txt file"

# 6. Watch output
docker-compose exec backend cline task view --follow-complete --address 127.0.0.1:41987
```

### Debug with Python

```python
# Run Python interactively in container
docker-compose exec backend python

>>> import asyncio
>>> from modules.execution_engine.cli_client import ClineCliClient
>>> client = ClineCliClient()
>>> 
>>> # Test clone
>>> asyncio.run(client._clone_repository("https://github.com/user/repo.git", "main"))
```

---

## Troubleshooting Flowchart

```
START: Task not working
         │
         ▼
    Is CLI installed?
    (cline --version)
         │
    NO ──┼── Rebuild Docker image
         │   docker-compose build backend
    YES  │
         ▼
    Are instances listed?
    (cline instance list)
         │
    NO ──┼── Create new instance
         │   Check backend logs for errors
    YES  │
         ▼
    Is task running?
    (cline task view --address X)
         │
    NO ──┼── Check if task was created
         │   Look for "task new" in logs
    YES  │
         ▼
    Is task progressing?
    (watch output for new lines)
         │
    NO ──┼── Check if waiting for approval
         │   Try: cline task send --approve
         │   Check API key validity
    YES  │
         ▼
    Task should complete eventually
    Check for errors in output
```

---

## Quick Reference Commands

```powershell
# Check everything is working
docker-compose exec backend cline --version
docker-compose exec backend cline instance list

# View current task
docker-compose exec backend cline task view --address ADDRESS

# Follow live output
docker-compose exec backend cline task view --follow-complete --address ADDRESS

# Approve pending action
docker-compose exec backend cline task send --approve --address ADDRESS

# Kill stuck instance
docker-compose exec backend cline instance kill ADDRESS

# View backend logs
docker-compose logs -f backend

# Enter container for debugging
docker-compose exec backend bash

# Clean up workspaces
docker-compose exec backend rm -rf /home/app/workspaces/run-*

# Restart everything fresh
docker-compose down
docker-compose up -d
```

---

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `CLINE_DIR` | Cline config directory | `/home/app/.cline` |
| `CLINE_PROVIDER` | LLM provider ID | `anthropic` |
| `CLINE_API_KEY` | Provider API key | `sk-ant-...` |
| `CLINE_MODEL_ID` | Model to use | `claude-sonnet-4-5-20250929` |
| `CLINE_BASE_URL` | Custom API endpoint | `https://api.example.com` |

---

## Getting Help

1. **Backend logs:** `docker-compose logs -f backend`
2. **Cline CLI help:** `docker-compose exec backend cline --help`
3. **Cline task help:** `docker-compose exec backend cline task --help`
4. **Check GitHub issues:** [cline/cline](https://github.com/cline/cline/issues)
5. **Cline documentation:** [docs.cline.bot](https://docs.cline.bot/)

---

## Summary

| Action | Command |
|--------|---------|
| Check CLI | `docker-compose exec backend cline --version` |
| List instances | `docker-compose exec backend cline instance list` |
| View task | `docker-compose exec backend cline task view --address ADDR` |
| Follow task | `docker-compose exec backend cline task view --follow-complete --address ADDR` |
| Approve | `docker-compose exec backend cline task send --approve --address ADDR` |
| Kill instance | `docker-compose exec backend cline instance kill ADDR` |
| View logs | `docker-compose logs -f backend` |
| Debug shell | `docker-compose exec backend bash` |
