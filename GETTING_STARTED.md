# Getting Started with slack-cline

This guide walks you through setting up the complete slack-cline system from scratch.

# Documentation 
- GETTING_STARTED.md - Complete walkthrough with troubleshooting
- CLINE_CORE_INTEGRATION.md - Deep dive into gRPC integration
- IMPLEMENTATION_SUMMARY.md - Architecture and decisions
- implementation_plan.md - Original technical specification
- README.md - Updated with correct setup instructions

## Overview

You'll be setting up two main components (all via Docker):
1. **PostgreSQL Database** - Stores run history and channel mappings
2. **slack-cline Backend** - FastAPI service with embedded Cline CLI

**Note:** The backend container includes Cline CLI, which automatically manages Cline Core instances and workspaces. No separate Cline Core service needed!

## Prerequisites

- Docker and Docker Compose installed
- Python 3.12+ (optional, for local development)
- A Slack workspace where you can install apps
- Git (pre-installed in Docker container)

## Step 1: Initial Setup

### 1.1 Clone and Configure

```bash
# Navigate to the slack-cline directory
cd slack-cline

# Copy environment template
cp .env.example .env
```

### 1.2 Configure Slack App First

Before building, set up your Slack app to get credentials (see Step 2).

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

## Step 3: Build and Start

### 3.1 Build Docker Images (First Time Only)

```powershell
cd C:\Users\naman\sline\slack-cline

# Build the backend (installs Node.js + Cline CLI inside)
docker-compose build

# This takes 3-5 minutes:
# - Installs Node.js 20 in Python container
# - Installs Cline CLI globally (npm install -g cline)
# - Installs Python dependencies
# - Downloads PostgreSQL image
```

### 3.2 Start Services

```powershell
# Start everything
docker-compose up

# Or run in background:
docker-compose up -d
docker-compose logs -f backend  # View logs
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
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

## Step 5: How It Works

### Architecture

```
Slack → Backend (FastAPI) → Cline CLI → Cline Core → Git Repos
           ↓
      PostgreSQL
```

**When you run `/cline run "task"`:**
1. Backend receives Slack webhook
2. Backend calls `cline instance new` in a cloned repo workspace
3. Cline CLI starts Cline Core automatically
4. Backend calls `cline task new -y "task"`
5. Backend streams output with `cline task view --follow`
6. Progress updates posted to Slack
7. Cleanup: `cline instance kill` when done

### Development Workflow

```powershell
# Start services
cd C:\Users\naman\sline\slack-cline
docker-compose up

# In another terminal: Expose to Slack
ngrok http 8000

# Test from Slack
/cline run create a hello world script
```

### Hot Reload

The backend supports hot reload in development:
- Edit Python files
- FastAPI automatically reloads
- No restart needed

## Troubleshooting

### "Cline CLI not found"

**Rebuild the Docker image:**
```powershell
docker-compose build backend
```

The Dockerfile installs Cline CLI automatically via `npm install -g cline`.

### "git clone failed"

**Check repository URL** in database or code:
- Must be a valid Git repository
- Must be publicly accessible OR have credentials configured
- For private repos, you'll need to add SSH keys or tokens

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

**How Workspaces Work:**
- Each run clones the repository to `/home/app/workspaces/run-TIMESTAMP/`
- Cline CLI runs in that directory
- After completion, workspace is automatically cleaned up

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
