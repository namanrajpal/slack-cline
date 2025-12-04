# Getting Started with slack-cline

This guide walks you through setting up the complete slack-cline system from scratch.

# Documentation 
- GETTING_STARTED.md - Complete walkthrough with troubleshooting
- CLINE_CORE_INTEGRATION.md - Deep dive into gRPC integration
- IMPLEMENTATION_SUMMARY.md - Architecture and decisions
- implementation_plan.md - Original technical specification
- README.md - Updated with correct setup instructions

## Overview

You'll be setting up three main components:
1. **PostgreSQL Database** - Stores run history and channel mappings
2. **Cline Core** - The AI agent gRPC server (from the main Cline project)
3. **slack-cline Backend** - FastAPI service that connects Slack to Cline Core

## Prerequisites

- Docker and Docker Compose installed
- Node.js 18+ (for Cline Core)
- Python 3.12+ (optional, for local development)
- A Slack workspace where you can install apps
- Git and basic command line knowledge

## Step 1: Initial Setup

### 1.1 Clone and Configure

```bash
# Navigate to the slack-cline directory
cd slack-cline

# Copy environment template
cp .env.example .env
```

### 1.2 Set Up Cline Core (First Time)

Cline Core is the gRPC server that runs the actual AI agent. You need to compile it once:

```bash
# Navigate to the Cline directory
cd ../cline

# Install dependencies
npm install

# Compile the standalone Cline Core
npm run compile-standalone

# This creates dist-standalone/cline-core.js
```

### 1.3 Compile Proto Files

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

## Step 3: Run the System Locally

### 3.1 Terminal 1: Start Cline Core

```bash
cd cline
node dist-standalone/cline-core.js --port 50051
```

You should see:
```
Starting cline-core service...
Registered instance in SQLite locks: 127.0.0.1:50051
All services started successfully
```

### 3.2 Terminal 2: Start PostgreSQL

```bash
cd slack-cline
docker-compose up db -d
```

Wait ~5 seconds for PostgreSQL to initialize.

### 3.3 Terminal 3: Start Backend

```bash
cd slack-cline

# If using Docker:
docker-compose up backend

# Or run locally:
cd backend
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3.4 Terminal 4: Expose with ngrok

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

### Quick Start (All-in-One)

For future development sessions:

```bash
# Terminal 1: Cline Core
cd cline && node dist-standalone/cline-core.js

# Terminal 2: slack-cline
cd slack-cline && docker-compose up

# Terminal 3: ngrok (if testing with Slack)
ngrok http 8000
```

### Docker-Only Development

Update `docker-compose.yml` to build Cline Core as a container (advanced).

### Hot Reload

The backend supports hot reload in development:
- Edit Python files
- FastAPI automatically reloads
- No restart needed

## Troubleshooting

### "Failed to connect to Cline Core"

**Check if Cline Core is running:**
```bash
# Windows
netstat -ano | findstr :50051

# macOS/Linux
lsof -i :50051
```

**Start Cline Core if not running:**
```bash
cd cline
node dist-standalone/cline-core.js --port 50051
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

**To customize:**
Edit the repository URL in `modules/orchestrator/service.py`:
```python
repo_url="https://github.com/your-org/your-repo.git"
```

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
