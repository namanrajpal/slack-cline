# Getting Started with slack-cline

This guide walks you through setting up the complete slack-cline system from scratch.

# Documentation 
- GETTING_STARTED.md - Complete walkthrough with troubleshooting
- CLINE_CORE_INTEGRATION.md - Deep dive into gRPC integration
- IMPLEMENTATION_SUMMARY.md - Architecture and decisions
- implementation_plan.md - Original technical specification
- README.md - Updated with correct setup instructions

## Overview

You'll be setting up three main components (all via Docker):
1. **PostgreSQL Database** - Stores run history and channel mappings
2. **Cline Core** - The AI agent gRPC server (compiled in Linux container)
3. **slack-cline Backend** - FastAPI service that connects Slack to Cline Core

## Prerequisites

- Docker and Docker Compose installed
- Python 3.12+ (for proto compilation only)
- A Slack workspace where you can install apps
- Git for cloning test repositories

**Note:** You do NOT need Node.js locally - Cline Core compiles and runs inside Docker (Linux).

## Step 1: Initial Setup

### 1.1 Clone and Configure

```bash
# Navigate to the slack-cline directory
cd slack-cline

# Copy environment template
cp .env.example .env
```

### 1.2 Compile Proto Files (Python Only)

slack-cline needs to generate Python gRPC client code from Cline's proto definitions:

```bash
# Navigate back to slack-cline
cd ../slack-cline

# Install Python dependencies (in a virtual environment)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Compile proto files
cd backend
python compile_protos.py
cd ..
```

You should see output like:
```
Compiling Cline proto files...
✓ Successfully compiled task.proto
✓ Successfully compiled state.proto
✓ Successfully compiled ui.proto
✓ Successfully compiled common.proto
✓ Successfully compiled checkpoints.proto
✓ All proto files compiled successfully!
```

## Step 2: Configure Slack App

### 2.1 Create Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App"
3. Choose "From scratch"
4. Name it "Cline Bot" and select your workspace

### 2.2 Configure Slash Commands

In your Slack app settings:

**Slash Commands** → **Create New Command**:
- **Command**: `/cline`
- **Request URL**: `https://your-ngrok-url.ngrok.io/slack/events` (see Step 3 for ngrok)
- **Short Description**: "Trigger Cline AI runs"
- **Usage Hint**: `run <task description>`

### 2.3 Configure Interactivity

**Interactivity & Shortcuts** → **Enable Interactivity**:
- **Request URL**: `https://your-ngrok-url.ngrok.io/slack/interactivity`

### 2.4 Set Bot Scopes

**OAuth & Permissions** → **Bot Token Scopes**:
- Add `chat:write` - Post messages
- Add `commands` - Receive slash commands

### 2.5 Install to Workspace

**Install App** → **Install to Workspace**

After installation, you'll get:
- **Bot User OAuth Token** - starts with `xoxb-`
- **Signing Secret** - in **Basic Information** → **App Credentials**

### 2.6 Update Environment

Edit `slack-cline/.env`:
```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
```

## Step 3: Build and Start All Services

### 3.1 Build Everything (First Time Only)

This builds Cline Core in a Linux container (avoiding Windows compilation issues):

```powershell
cd C:\Users\naman\sline\slack-cline

# Build all images (this compiles Cline Core in Linux!)
docker-compose build

# This will take 5-10 minutes on first run
# - Compiles Cline Core in Alpine Linux (no Windows issues)
# - Builds Python backend container
# - Downloads PostgreSQL image
```

### 3.2 Start All Services

```powershell
# Start everything
docker-compose up

# Or run in background:
docker-compose up -d

# View logs:
docker-compose logs -f
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3.3 Expose with ngrok (Separate Terminal)

For local development, expose your backend to the internet:

```bash
ngrok http 8000
```

You'll see something like:
```
Forwarding https://abc123.ngrok.io -> http://localhost:8000
```

**Update your Slack app URLs** with this ngrok URL:
- Slash command: `https://abc123.ngrok.io/slack/events`
- Interactivity: `https://abc123.ngrok.io/slack/interactivity`

## Step 4: Test the Integration

### 4.1 Verify Health

```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy","service":"slack-cline-backend"}
```

### 4.2 Test from Slack

1. Go to any channel in your Slack workspace
2. Invite the Cline bot: `/invite @Cline Bot`
3. Run a command:
   ```
   /cline run create a hello world Python script
   ```

You should see:
- ✅ Immediate response in Slack
- 🔧 Progress updates as Cline works
- ✅ or ❌ Final completion status

### 4.3 Check Logs

```bash
# Backend logs
docker-compose logs -f backend

# Or if running locally:
# Check terminal where you ran python main.py
```

You should see:
```json
{"event": "Slack slash_command_received", "channel_id": "C123...", "command": "/cline"}
{"event": "Run created", "run_id": "abc-123", "task_prompt": "create a hello..."}
{"event": "gRPC TaskService.NewTask", "success": true, "task_id": "task_xyz"}
{"event": "Run execution_started", "cline_run_id": "task_xyz"}
```

## Step 5: Development Workflow

### Quick Start (All Services via Docker)

For future development sessions:

```powershell
# Start everything
cd C:\Users\naman\sline\slack-cline
docker-compose up

# In another terminal: Expose to Slack
ngrok http 8000
```

That's it! Docker handles:
- ✅ Cline Core compilation (in Linux)
- ✅ PostgreSQL database
- ✅ Python backend

### Hot Reload

The backend supports hot reload in development:
- Edit Python files
- FastAPI automatically reloads
- No restart needed

## Troubleshooting

### "Failed to connect to Cline Core"

**Check if Cline Core container is running:**
```powershell
docker-compose ps cline-core
# Should show "Up"
```

**View Cline Core logs:**
```powershell
docker-compose logs cline-core
# Should see: "All services started successfully"
```

**Restart Cline Core:**
```powershell
docker-compose restart cline-core
```

### "gRPC proto modules not found"

**Compile the proto files:**
```bash
cd slack-cline/backend
python compile_protos.py
```

### "Slack signature verification failed"

**Check your `.env` file:**
- Ensure `SLACK_SIGNING_SECRET` matches your Slack app
- No extra spaces or quotes
- Restart the backend after changing `.env`

### "No repository configured for channel"

This is expected for MVP! The system auto-creates a default repository mapping.

**For MVP:** Edit `backend/modules/orchestrator/service.py` (line ~130):
```python
project = ProjectModel(
    tenant_id=tenant_id,
    slack_channel_id=channel_id,
    repo_url="/workspaces/demo",  # Docker volume path
    default_ref="main"
)
```

**For production:** Configure via database with actual Git URLs:
```sql
INSERT INTO projects VALUES (
    gen_random_uuid(),
    'default',
    'YOUR_SLACK_CHANNEL_ID',
    'https://github.com/your-org/your-repo.git',  # Real Git URL
    'main',
    NOW(),
    NOW()
);
```

**Workspace Management:**
For MVP, use Docker volumes. For production, add automatic git cloning logic in the execution engine.

### Backend won't start

**Check Python version:**
```bash
python --version  # Should be 3.12+
```

**Reinstall dependencies:**
```bash
pip install -r requirements.txt
```

**Check database connection:**
```bash
docker-compose up db -d
# Wait 5 seconds
docker-compose ps  # db should be "Up"
```

## Architecture Refresher

```
User in Slack
    ↓ /cline run "task"
Slack App (webhook)
    ↓ HTTP POST
Backend (FastAPI)
    ↓ gRPC
Cline Core (Node.js)
    ↓ 
AI Agent executes task
    ↓ Events
Backend receives events
    ↓ HTTP POST
Slack shows progress
```

## Next Steps

### 1. Configure Repository Mappings

For production, you'll want to configure which repositories map to which Slack channels.

Create a `projects.json` or use the database directly:
```sql
INSERT INTO projects (tenant_id, slack_channel_id, repo_url, default_ref)
VALUES ('default', 'C123ABC', 'https://github.com/org/repo.git', 'main');
```

### 2. Set Up CI/CD

Deploy to a cloud provider:
- Build Docker images
- Deploy to ECS, K8s, or similar
- Use managed PostgreSQL (RDS, Cloud SQL)
- Run Cline Core as sidecar or separate service

### 3. Add Authentication

For production Slack apps:
- Implement OAuth flow
- Support multiple workspaces (multi-tenant)
- Add user permissions and ACLs

### 4. Monitoring

Add monitoring and observability:
- Application metrics (Prometheus)
- Error tracking (Sentry)
- Distributed tracing (OpenTelemetry)
- Log aggregation (ELK, Datadog)

## Useful Commands

```bash
# View backend logs
docker-compose logs -f backend

# View database
docker-compose exec db psql -U postgres -d slack_cline

# List tables
\dt

# View runs
SELECT id, status, task_prompt, created_at FROM runs ORDER BY created_at DESC LIMIT 10;

# Restart backend
docker-compose restart backend

# Full reset (deletes database)
docker-compose down -v
docker-compose up -d
```

## Reference Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) - Component details
- [CLINE_CORE_INTEGRATION.md](./CLINE_CORE_INTEGRATION.md) - gRPC integration guide
- [implementation_plan.md](./implementation_plan.md) - Implementation details
- [README.md](./README.md) - Project overview

## Support

Issues? Check:
1. All three components are running (Cline Core, PostgreSQL, Backend)
2. Proto files are compiled (`python backend/compile_protos.py`)
3. Environment variables in `.env` are correct
4. ngrok tunnel is active and URLs match Slack app config
5. Logs for error messages (`docker-compose logs -f backend`)

## Success! 🎉

If you can run `/cline run hello world` in Slack and see a response, you're all set!

The system is now:
- ✅ Receiving Slack commands
- ✅ Creating tasks in Cline Core
- ✅ Streaming progress back to Slack
- ✅ Tracking runs in PostgreSQL

Happy coding with Cline! 🤖
