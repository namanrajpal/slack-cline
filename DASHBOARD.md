# Dashboard User Guide

The slack-cline dashboard is your **testing and management interface** for the Slack-Cline integration.

## Quick Access

**Dashboard URL**: http://localhost:3001

**API URL**: http://localhost:8000

---

## Dashboard Pages

### 📊 Dashboard (Home)

**URL**: http://localhost:3001

**Features**:
- Overview stats (total projects, active runs, total runs)
- Recent projects (last 5)
- Recent runs (last 10) with status badges
- Quick action buttons

**Use When**: You want a high-level overview of system activity

---

### 🗂️ Projects

**URL**: http://localhost:3001/projects

**What It Does**: Manages Slack channel → Git repository mappings

**Features**:
- Table view of all projects
- Create new project with form:
  - Channel ID (e.g., `C12345678` or `C_TEST_CHANNEL`)
  - Repository URL (e.g., `https://github.com/org/repo.git`)
  - Default branch (e.g., `main`)
- Delete projects (with confirmation)

**Use When**: 
- Setting up a new Slack channel
- Changing which repo a channel uses
- Updating default branch

**Example**:
```
Channel: C_ENGINEERING
Repo: https://github.com/mycompany/backend-api.git
Branch: main
```

Now `/cline run` commands in #engineering will operate on backend-api repository.

---

### 🏃 Runs

**URL**: http://localhost:3001/runs

**What It Does**: Shows execution history of all Cline runs

**Features**:
- Table with status badges (⏳ queued, 🔧 running, ✅ succeeded, ❌ failed, ⚠️ cancelled)
- Filter by status dropdown
- Shows task prompt, channel, created time, duration
- Hover for full details

**Use When**:
- Monitoring active runs
- Reviewing execution history
- Debugging failed runs
- Checking task completion times

**Tip**: Refresh the page to see updated statuses (auto-refresh coming soon!)

---

### ⚙️ Settings

**URL**: http://localhost:3001/settings

**What It Does**: Configure LLM provider credentials

**Features**:
- Provider selection:
  - Anthropic (Claude)
  - OpenAI (GPT)
  - OpenRouter (multi-model)
  - Google Gemini
  - xAI (Grok)
  - Ollama (local)
  - OpenAI-Compatible (Azure, etc.)
- API key input (masked when displayed)
- Model ID configuration
- Optional base URL (for OpenAI-compatible)
- Provider documentation links

**Use When**:
- Initial setup
- Changing LLM providers
- Updating API keys
- Testing different models

⚠️ **Important**: After saving, restart the backend:
```bash
docker-compose restart backend
```

**Security Note**: API keys are stored in `.env` file. Never commit this file!

---

### 🧪 Admin Panel

**URL**: http://localhost:3001/admin

**What It Does**: Simulate Slack commands for testing **without using Slack**

**Features**:
- Channel/project selection dropdown
- Task description textarea
- Quick-fill buttons for common tasks:
  - "Create README"
  - "Add Tests"  
  - "Fix Linting"
- Submit button (simulates `/cline run` command)
- Results display:
  - Success/failure status
  - Request payload (what was sent)
  - Response payload (what was received)
  - Link to view created run

**Use When**:
- Testing your setup before Slack integration
- Debugging issues without Slack complexity
- Validating changes to backend
- Quick iteration during development

**How It Works**:
```
Admin Panel Form
    ↓ Constructs Slack-like payload
POST /api/test/slack-command
    ↓ Calls handle_cline_command() directly
Same backend logic as real Slack
    ↓ Creates run, clones repo, executes
Results displayed in panel
```

**Testing Workflow**:
1. Select channel: `C_TEST_CHANNEL`
2. Enter task: "create a simple Python calculator"
3. Click "Simulate Slack Command"
4. View results panel (should show success)
5. Go to Runs page to see execution
6. Check backend logs: `docker-compose logs -f backend`

---

## Testing Best Practices

### Development Testing (Admin Panel)

**Before deploying to Slack**, validate with Admin Panel:

```
✅ Create test project with your repo
✅ Configure API keys in Settings
✅ Run simple task: "create a README"
✅ Verify in Runs page
✅ Check backend logs for errors
✅ Confirm workspace cleanup
```

### Integration Testing (Slack)

**After dashboard validation**, test with Slack:

```
✅ Set up Slack app
✅ Expose with ngrok
✅ Test slash command
✅ Verify progress updates in thread
✅ Compare behavior with dashboard
✅ Check both show same runs
```

### Debugging Workflow

**When something fails**:

1. **Runs Page**: Check status and error message
2. **Backend Logs**: `docker-compose logs -f backend`
3. **Database**: Query for details
4. **Admin Panel**: Retry same command for easier debugging
5. **Fix Issue**: Update code/config
6. **Test Again**: Use Admin Panel first, then Slack

---

## Common Tasks

### Create Project for Slack Channel

1. Get channel ID from Slack:
   - Right-click channel → View channel details
   - Scroll down to copy channel ID
2. Go to Projects page
3. Click "+ New Project"
4. Enter channel ID and repository
5. Save

### Update API Keys

1. Go to Settings page
2. Select provider
3. Enter new API key and model
4. Save
5. **Restart backend**: `docker-compose restart backend`

### Test a New Feature

1. Make code changes
2. Restart backend if needed
3. Go to Admin Panel
4. Select test channel
5. Enter task testing your feature
6. Submit and review results
7. Check Runs page for execution details

### Monitor Active Runs

1. Go to Runs page
2. Filter by status: "running"
3. Refresh to see updates
4. Click on run for full details

### Debug Failed Run

1. Find failed run in Runs page
2. Note the error summary
3. Check backend logs around that timestamp:
   ```bash
   docker-compose logs backend | grep <run-id>
   ```
4. Reproduce in Admin Panel with simpler task
5. Fix issue
6. Retry

---

## API Reference

### Projects API

```typescript
// List all projects
GET /api/projects
Response: Project[]

// Create project
POST /api/projects
Body: { slack_channel_id, repo_url, default_ref }
Response: Project

// Update project
PUT /api/projects/{id}
Body: { repo_url?, default_ref? }
Response: Project

// Delete project
DELETE /api/projects/{id}
Response: 204 No Content
```

### Runs API

```typescript
// List runs (with filters)
GET /api/runs?status=running&project_id=xxx&limit=50
Response: Run[]

// Get run details
GET /api/runs/{id}
Response: Run
```

### Configuration API

```typescript
// Get API config (masked)
GET /api/config/api-keys
Response: ApiKeyConfig

// Update API config
POST /api/config/api-keys
Body: { provider, api_key, model_id, base_url? }
Response: { success, message, restart_required }
```

### Test API

```typescript
// Simulate Slack command
POST /api/test/slack-command
Body: { channel_id, text, user_id?, team_id? }
Response: { success, message, request_payload, response_payload }
```

---

## Dashboard Architecture

```
┌─────────────────────────────────────┐
│  React Frontend (Vite + Tailwind)  │
│  Port: 3001                         │
│  - Projects management              │
│  - Run monitoring                   │
│  - Settings configuration           │
│  - Admin testing panel              │
└─────────────┬───────────────────────┘
              │ HTTP/REST
              ↓
┌─────────────────────────────────────┐
│  FastAPI Backend                    │
│  Port: 8000                         │
│  - /slack/* (Slack webhooks)        │
│  - /api/* (Dashboard API)           │
└─────────────┬───────────────────────┘
              │
              ↓
┌─────────────────────────────────────┐
│  PostgreSQL Database                │
│  Port: 5432                         │
│  - projects table                   │
│  - runs table                       │
└─────────────────────────────────────┘
```

---

## Keyboard Shortcuts

When dashboard is focused:

- **Navigate**: Click nav items or use browser back/forward
- **Refresh data**: Browser refresh (F5) or refresh button
- **Quick actions**: Use quick-fill buttons in Admin Panel
- **Forms**: Tab to navigate, Enter to submit

---

## Tips & Tricks

### Quick Database Check

Add this alias to your shell:
```bash
alias slack-cline-db="docker-compose -f C:/Users/naman/sline/slack-cline/docker-compose.yml exec db psql -U postgres -d slack_cline"

# Usage:
slack-cline-db -c "SELECT * FROM projects;"
```

### Monitor Logs in Real-Time

```bash
# In separate terminal
docker-compose logs -f backend | grep -E "(Test command|Run created|execution)"
```

### Test Different Providers

Use Settings page to quickly switch between providers:
1. Save Anthropic config → Restart → Test
2. Save OpenAI config → Restart → Test
3. Compare results

### Bulk Project Creation

For multiple channels, use the API directly:
```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "slack_channel_id": "C_ANOTHER_CHANNEL",
    "repo_url": "https://github.com/org/another-repo.git",
    "default_ref": "develop"
  }'
```

---

## Future Enhancements

Planned features for the dashboard:

- [ ] Real-time run updates (WebSocket)
- [ ] Run cancellation button
- [ ] Detailed run logs viewer
- [ ] Run history charts
- [ ] Project usage statistics
- [ ] API key encryption
- [ ] User authentication
- [ ] Role-based access control
- [ ] Export run history (CSV, JSON)
- [ ] Workspace file browser

---

## Development Notes

The dashboard is built with:
- **React 18** - UI framework
- **Vite** - Build tool (fast hot reload)
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **React Router** - Navigation
- **Axios** - API client
- **date-fns** - Date formatting

Source code: `slack-cline/frontend/src/`

---

For questions or issues, check:
- Backend logs: `docker-compose logs -f backend`
- Browser console: F12 → Console tab
- Network tab: F12 → Network tab (see API requests)
- Database: `docker-compose exec db psql -U postgres -d slack_cline`

Happy testing! 🎉
