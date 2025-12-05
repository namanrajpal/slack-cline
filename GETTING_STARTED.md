# Getting Started with slack-cline

This guide walks you through setting up and testing the complete slack-cline system.

## Documentation Overview

- **GETTING_STARTED.md** - Complete setup walkthrough (this file)
- **DASHBOARD.md** - Dashboard features and usage guide
- **FINAL_ARCHITECTURE.md** - Current CLI-based architecture
- **CLINE_CLI_AUTHENTICATION.md** - API key configuration guide
- **SYSTEM_ARCHITECTURE.md** - Detailed component breakdown
- **README.md** - Project overview

---

## What You're Building

**slack-cline** is a Slack bot that brings Cline's AI coding capabilities directly into your Slack workspace. Team members can trigger autonomous coding tasks with simple slash commands like `/cline run fix failing tests`.

### System Components

```
┌─────────────┐
│   Slack     │ ← Primary interface (production)
│  Workspace  │
└──────┬──────┘
       │ /cline run <task>
       ↓
┌─────────────────────────────┐
│   Backend (FastAPI)         │
│   - Slack webhooks          │
│   - Dashboard API           │ ← Testing/debugging interface
│   - Cline CLI integration   │
└──────┬──────────────────────┘
       │
       ↓
┌─────────────┐    ┌─────────────┐
│ PostgreSQL  │    │  Cline CLI  │
│  Database   │    │   + Core    │
└─────────────┘    └─────────────┘
```

**Dashboard Purpose**: Test your integration and manage configuration **before** moving to Slack. Think of it as your development/debugging console.

---

## Prerequisites

- **Docker & Docker Compose** - For running services
- **Node.js 18+** - For frontend dashboard (optional)
- **Git** - Pre-installed in Docker container
- **Slack Workspace** - Where you can install apps (for production use)
- **LLM API Key** - Anthropic, OpenAI, OpenRouter, etc.

---

## Quick Start (5 Minutes)

### Step 1: Start the Services

```powershell
cd C:\Users\naman\sline\slack-cline

# Build containers (first time only)
docker-compose build

# Start all services
docker-compose up
```

You should see:
```
✅ PostgreSQL ready on port 5432
✅ Backend ready on port 8000
✅ Database tables created
```

### Step 2: Start the Dashboard (Separate Terminal)

```powershell
cd C:\Users\naman\sline\slack-cline\frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

Dashboard will be available at: **http://localhost:3001**

### Step 3: Verify Health

```bash
# Backend API
curl http://localhost:8000/health

# Dashboard API
curl http://localhost:8000/api/health

# Interactive API docs
# Open: http://localhost:8000/docs
```

---

## Testing Workflow (Before Slack)

Use the dashboard to validate your setup works correctly before configuring Slack.

### 1. Create a Project Mapping

**Projects Page** → http://localhost:3001/projects

Click **"+ New Project"** and enter:
- **Channel ID**: `C_TEST_CHANNEL` (or real Slack channel ID)
- **Repository URL**: `https://github.com/your-username/your-repo.git`
- **Default Branch**: `main`

This maps a Slack channel to a Git repository.

### 2. Configure API Keys

**Settings Page** → http://localhost:3001/settings

1. Select your LLM provider (Anthropic, OpenAI, etc.)
2. Enter your API key
3. Enter model ID (e.g., `claude-sonnet-4-5-20250929`)
4. Click **"Save Configuration"**

⚠️ **Important**: Restart the backend after saving:
```bash
docker-compose restart backend
```

### 3. Test with Admin Panel

**Admin Panel** → http://localhost:3001/admin

This simulates Slack commands **without actually using Slack**:

1. Select your channel from the dropdown
2. Enter a task description:
   - "create a README file"
   - "add unit tests to utils.py"
   - "fix linting errors"
3. Click **"Simulate Slack Command"**

**What happens**:
- ✅ Same execution flow as real Slack
- ✅ Calls actual `/slack/events` endpoint
- ✅ Creates run in database
- ✅ Cline clones repo and executes task
- ✅ You see request/response payloads

### 4. Monitor Execution

**Runs Page** → http://localhost:3001/runs

Watch your runs in real-time:
- Status badges (queued → running → succeeded/failed)
- Task descriptions
- Timestamps and duration
- Execution details

**Or check database directly**:
```bash
docker-compose exec db psql -U postgres -d slack_cline

# List runs
SELECT id, status, task_prompt, created_at FROM runs ORDER BY created_at DESC LIMIT 10;

# Check workspaces
\! ls -la /home/app/workspaces/
```

### 5. View Backend Logs

```bash
# Real-time logs
docker-compose logs -f backend

# Look for:
✅ "Test command simulation: /cline run <task>"
✅ "Cloned <repo> to /home/app/workspaces/run-XXX/"
✅ "Created Cline instance at localhost:50052"
✅ "Streaming events from CLI..."
```

---

## Production Setup (Slack Integration)

Once you've validated everything works with the dashboard, set up Slack for production use.

### Step 1: Create Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"** → **"From scratch"**
3. Name: **"Cline Bot"**
4. Select your workspace

### Step 2: Configure Slash Command

**Slash Commands** → **Create New Command**:

- **Command**: `/cline`
- **Request URL**: `https://your-ngrok-url.ngrok.io/slack/events` *(see Step 3)*
- **Short Description**: "Trigger Cline AI coding tasks"
- **Usage Hint**: `run <task description>`

### Step 3: Expose Backend with ngrok

In a **new terminal** (keep docker-compose running):

```bash
ngrok http 8000
```

You'll get a forwarding URL like:
```
Forwarding https://abc123.ngrok-free.app -> http://localhost:8000
```

**Update Slack app URLs** with this ngrok URL:
- Slash command: `https://abc123.ngrok-free.app/slack/events`
- Interactivity: `https://abc123.ngrok-free.app/slack/interactivity`

### Step 4: Configure Bot Permissions

**OAuth & Permissions** → **Bot Token Scopes**:
- Add `chat:write` - Post messages to channels
- Add `commands` - Receive slash commands

### Step 5: Install to Workspace

**Install App** → **Install to Workspace**

After installation, copy:
- **Bot User OAuth Token** (starts with `xoxb-`)
- **Signing Secret** (in Basic Information → App Credentials)

### Step 6: Update Environment

Edit `slack-cline/backend/.env`:
```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here

# Your LLM configuration
CLINE_PROVIDER=anthropic
CLINE_API_KEY=sk-ant-your-key-here
CLINE_MODEL_ID=claude-sonnet-4-5-20250929
```

Restart backend:
```bash
docker-compose restart backend
```

### Step 7: Test from Slack

1. Go to any channel in your Slack workspace
2. Invite the bot: `/invite @Cline Bot`
3. **Ensure this channel has a project mapping** (use Dashboard's Projects page)
4. Run a command:
   ```
   /cline run create a hello world Python script
   ```

You should see:
- ✅ Immediate response: "🚀 Starting Cline run..."
- 🔧 Progress updates as Cline works
- ✅ Final summary when complete

### Step 8: Monitor via Dashboard

While Slack runs are executing:
- **Runs page**: See all Slack-triggered runs
- **Dashboard**: Monitor active/completed runs
- **Database**: Track execution history

---

## End-to-End Testing Guide

### Scenario 1: Dashboard Testing (Quick Validation)

**Purpose**: Verify your setup without Slack

```bash
1. Start services: docker-compose up
2. Start dashboard: cd frontend && npm run dev
3. Create project: http://localhost:3001/projects
4. Configure API: http://localhost:3001/settings
5. Test run: http://localhost:3001/admin
6. Monitor: http://localhost:3001/runs
7. Check database: docker-compose exec db psql -U postgres -d slack_cline
```

### Scenario 2: Slack Integration (Production Flow)

**Purpose**: Real-world usage

```bash
1. Keep services running
2. Set up Slack app (Steps 1-6 above)
3. Start ngrok: ngrok http 8000
4. Update Slack URLs with ngrok
5. Test from Slack channel
6. Monitor in Slack thread + dashboard
```

### Scenario 3: Debugging Failed Runs

**When a run fails**:

```bash
1. Check Runs page: Status and error message
2. Check backend logs: docker-compose logs -f backend
3. Check database:
   docker-compose exec db psql -U postgres -d slack_cline \
     -c "SELECT id, status, summary FROM runs WHERE status='failed';"
4. Check workspace (if not cleaned up):
   docker-compose exec backend ls -la /home/app/workspaces/
5. Test same command in Admin Panel for easier debugging
```

---

## Dashboard Features Reference

### 📊 Dashboard (Home)
- **Stats Cards**: Project count, active runs, total runs
- **Recent Projects**: Last 5 configured projects
- **Recent Runs**: Last 10 executions with status
- **Quick Actions**: Links to key pages

### 🗂️ Projects Page
- **List all projects**: Channel→repository mappings
- **Create new**: Add channel configurations
- **Delete projects**: Remove mappings (also deletes associated runs)

**Use Case**: Configure which repos Slack channels can execute on

### 🏃 Runs Page
- **Run history**: All executions with filters
- **Status filtering**: queued, running, succeeded, failed, cancelled
- **Project filtering**: See runs for specific channel
- **Details**: Task prompt, timestamps, duration, workspace path

**Use Case**: Monitor execution history and debug failures

### ⚙️ Settings Page
- **Provider selection**: Anthropic, OpenAI, OpenRouter, Gemini, etc.
- **API key management**: Configure LLM credentials
- **Model configuration**: Set model IDs
- **Warning**: Shows restart requirement

**Use Case**: Manage LLM provider credentials

### 🧪 Admin Panel
- **Simulate Slack commands**: Test without Slack setup
- **Channel selection**: Choose from configured projects
- **Task input**: Enter any coding task
- **Results display**: Request/response payloads
- **Quick fill buttons**: Common test tasks

**Use Case**: Test integration, debug issues, validate before Slack deployment

---

## Architecture Flow

### Production Flow (Slack)

```
User in Slack
   ↓ /cline run "task"
Slack App (webhook)
   ↓ POST /slack/events
Backend validates signature
   ↓ Creates run in database
Backend calls Cline CLI
   ↓ Clones repo to workspace
Cline Core executes task
   ↓ Streams output
Backend posts to Slack
   ↓ Progress updates in thread
User sees results
```

### Testing Flow (Dashboard)

```
User in Dashboard
   ↓ Admin Panel form
POST /api/test/slack-command
   ↓ Calls handle_cline_command() directly
Same flow as above (no Slack)
   ↓ Creates run in database
Cline executes task
   ↓ Results in Runs page
User sees results in dashboard
```

**Key Point**: Dashboard uses the **exact same backend logic** as Slack, just bypassing the webhook layer.

---

## Troubleshooting

### Dashboard Won't Load

**Symptoms**: Frontend errors, blank page

**Solutions**:
1. Check Vite is running: `npm run dev` in frontend folder
2. Check port: Should be http://localhost:3001
3. Check browser console for errors
4. Restart Vite server

### "Failed to load projects"

**Symptoms**: API error in dashboard

**Solutions**:
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check CORS in logs: Should allow localhost:3001
3. Check browser network tab: Should reach http://localhost:8000/api/projects
4. Verify database: `docker-compose ps` (db should be "Up")

### "Configuration error: No repository configured"

**Symptoms**: Slack or Admin Panel says channel not configured

**Solutions**:
1. Go to Projects page
2. Create mapping for the channel ID
3. Verify in database:
   ```sql
   SELECT slack_channel_id, repo_url FROM projects;
   ```

### "Failed to start run"

**Symptoms**: Run doesn't start, immediate error

**Check**:
1. **API keys configured**: Settings page or `.env` file
2. **Backend restarted** after changing API keys
3. **Repository accessible**: Try cloning manually
4. **Logs**: `docker-compose logs -f backend`

### Slack Signature Verification Failed

**Symptoms**: Slack commands return "Unauthorized"

**Solutions**:
1. Check `SLACK_SIGNING_SECRET` in `.env` matches Slack app
2. Verify no extra spaces or quotes in `.env`
3. Restart backend: `docker-compose restart backend`
4. Check ngrok is running and URL is correct

### Cline CLI Not Found

**Symptoms**: "cline: command not found" in logs

**Solutions**:
1. Rebuild Docker image: `docker-compose build backend`
2. Verify installation: `docker-compose exec backend cline --version`
3. Check Dockerfile includes: `RUN npm install -g cline`

---

## Database Inspection

### Quick Checks

```bash
# Connect to database
docker-compose exec db psql -U postgres -d slack_cline

# List tables
\dt

# View all projects
SELECT slack_channel_id, repo_url, default_ref FROM projects;

# View recent runs
SELECT id, status, task_prompt, created_at 
FROM runs 
ORDER BY created_at DESC 
LIMIT 10;

# Count runs by status
SELECT status, COUNT(*) 
FROM runs 
GROUP BY status;

# Exit
\q
```

### Detailed Run Information

```sql
-- Get full run details
SELECT 
    r.id,
    r.status,
    r.task_prompt,
    r.cline_instance_address,
    r.workspace_path,
    r.created_at,
    r.started_at,
    r.finished_at,
    p.repo_url
FROM runs r
JOIN projects p ON r.project_id = p.id
WHERE r.id = '<run-id>';
```

---

## Useful Commands

### Docker Management

```bash
# View logs (real-time)
docker-compose logs -f backend

# View logs (last 100 lines)
docker-compose logs --tail=100 backend

# Restart services
docker-compose restart backend
docker-compose restart db

# Stop everything
docker-compose down

# Stop and delete database (fresh start)
docker-compose down -v

# Rebuild after code changes
docker-compose build backend
docker-compose up -d
```

### Database Operations

```bash
# Quick query
docker-compose exec db psql -U postgres -d slack_cline \
  -c "SELECT COUNT(*) FROM runs WHERE status='succeeded';"

# Backup database
docker-compose exec db pg_dump -U postgres slack_cline > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres slack_cline < backup.sql

# Clear all data
docker-compose exec db psql -U postgres -d slack_cline \
  -c "TRUNCATE runs, projects CASCADE;"
```

### Cline CLI Testing

```bash
# Check Cline CLI version
docker-compose exec backend cline --version

# Test instance creation (inside container)
docker-compose exec backend cline instance new

# List active instances
docker-compose exec backend cline instance list

# Kill an instance
docker-compose exec backend cline instance kill localhost:50052
```

---

## Development Workflow

### Typical Development Session

```powershell
# Terminal 1: Backend
cd slack-cline
docker-compose up

# Terminal 2: Frontend  
cd slack-cline/frontend
npm run dev

# Terminal 3: ngrok (when ready for Slack)
ngrok http 8000

# Browser: Dashboard
http://localhost:3001
```

### Making Changes

**Backend changes**:
1. Edit Python files
2. FastAPI auto-reloads (no restart needed)
3. For dependency changes: `docker-compose build backend`

**Frontend changes**:
1. Edit React files
2. Vite hot-reloads automatically
3. For dependency changes: `npm install`

**Database changes**:
1. Edit models in `backend/models/`
2. Restart: `docker-compose restart backend`
3. For schema changes: `docker-compose down -v && docker-compose up`

---

## Production Deployment Checklist

Before deploying to production:

### Security
- [ ] Remove ngrok, use proper domain
- [ ] Add SSL/TLS certificates
- [ ] Rotate API keys
- [ ] Enable Slack OAuth for multi-workspace
- [ ] Add authentication to dashboard
- [ ] Encrypt API keys in database

### Infrastructure
- [ ] Use managed PostgreSQL (RDS, Cloud SQL)
- [ ] Deploy to container platform (ECS, K8s, Cloud Run)
- [ ] Set up monitoring (Sentry, DataDog)
- [ ] Configure backup strategy
- [ ] Set up CI/CD pipeline

### Configuration
- [ ] Environment-specific `.env` files
- [ ] Secrets management (AWS Secrets, Vault)
- [ ] Separate production/staging environments
- [ ] Rate limiting for API endpoints

### Observability
- [ ] Application metrics (Prometheus)
- [ ] Error tracking (Sentry)
- [ ] Distributed tracing (OpenTelemetry)
- [ ] Log aggregation (ELK stack)

---

## Testing Checklist

### Dashboard Testing
- [ ] All pages load without errors
- [ ] Can create project mapping
- [ ] Can view project list
- [ ] Can delete project
- [ ] Can view run history
- [ ] Can filter runs by status
- [ ] Can update API keys
- [ ] Admin Panel simulates commands
- [ ] Results display correctly

### Integration Testing (Admin Panel)
- [ ] Select channel from dropdown
- [ ] Submit test command
- [ ] Run appears in database
- [ ] Cline execution starts
- [ ] Workspace created
- [ ] Repository cloned
- [ ] Task executes
- [ ] Workspace cleaned up
- [ ] Results visible in Runs page

### Slack Testing
- [ ] Slash command registered
- [ ] Bot invited to channel
- [ ] Channel has project mapping
- [ ] API keys configured
- [ ] `/cline run <task>` responds
- [ ] Progress updates post to thread
- [ ] Final summary shows results
- [ ] Run tracked in dashboard
- [ ] Can cancel with button (future)

---

## Advanced Features

### Custom Workflows

Create common tasks as quick actions in the Admin Panel (already has quick-fill buttons for common tasks).

### Multi-Workspace Support

For supporting multiple Slack workspaces:
1. Implement OAuth flow
2. Store credentials per tenant in database
3. Update authentication logic
4. Add tenant selection in dashboard

### Private Repository Access

For private repos:
1. Add SSH key management
2. Or use personal access tokens
3. Store in database encrypted
4. Configure during project creation

---

## Example Workflows

### Workflow 1: Fix Failing Tests

**Via Slack**:
```
/cline run analyze failing tests in test_utils.py and fix them
```

**Via Dashboard**:
1. Admin Panel → Select channel
2. Task: "analyze failing tests in test_utils.py and fix them"
3. Submit → Monitor in Runs page

### Workflow 2: Code Review

**Via Slack**:
```
/cline run review the changes in src/auth.py and suggest improvements
```

### Workflow 3: Documentation

**Via Slack**:
```
/cline run update README with installation instructions and usage examples
```

---

## Support & Troubleshooting

### Getting Help

1. **Check logs**: `docker-compose logs -f backend`
2. **Check database**: Use psql commands above
3. **Use Admin Panel**: Test without Slack complexity
4. **Review architecture docs**: FINAL_ARCHITECTURE.md

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "No projects" error | Channel not mapped | Create project in Projects page |
| Signature failed | Wrong Slack secret | Update `.env` and restart |
| Run fails immediately | No API key | Configure in Settings page |
| Git clone fails | Private repo | Add access credentials |
| Cline not found | Build issue | Rebuild: `docker-compose build backend` |

---

## Success Criteria

✅ **Setup Complete When**:
- Docker services running
- Database initialized
- Dashboard accessible
- Can create projects
- Can configure API keys

✅ **Testing Complete When**:
- Admin Panel simulates commands successfully
- Runs appear in database and dashboard
- Cline clones repo and executes tasks
- Can monitor execution in Runs page

✅ **Production Ready When**:
- Slack app configured
- Slash commands work in Slack
- ngrok or production domain set up
- Progress updates post to Slack threads
- Dashboard shows all activity

---

## Next Steps

1. **Complete dashboard testing** - Validate entire flow works
2. **Set up Slack app** - Configure for production use
3. **Deploy to cloud** - Move off localhost
4. **Add monitoring** - Track usage and errors
5. **Scale up** - Support multiple channels/workspaces

---

## Quick Reference

```bash
# Start system
docker-compose up

# Start dashboard
cd frontend && npm run dev

# Check health
curl http://localhost:8000/health

# Access dashboard
http://localhost:3001

# View database
docker-compose exec db psql -U postgres -d slack_cline

# View logs
docker-compose logs -f backend

# Restart services
docker-compose restart backend

# Full reset
docker-compose down -v && docker-compose up
```

---

Happy coding with slack-cline! 🤖🚀
