# Dashboard Guide

The Sline Dashboard is your **testing and configuration interface** - think of it as a development/debugging console for validating your setup before deploying to Slack.

**Dashboard URL:** http://localhost:3001

---

## 🎯 Dashboard Purpose

The dashboard serves three main purposes:

1. **Testing** - Test Sline's agent without setting up Slack
2. **Configuration** - Manage projects and API keys
3. **Debugging** - Inspect conversations and troubleshoot issues

> **Key Principle:** Dashboard is for development/testing. Slack is the production interface.

---

## 📊 Dashboard Pages

### 🏠 Home / Dashboard

**URL:** http://localhost:3001

**Features:**
- Project count overview
- Recent projects list
- Quick action buttons

**Use When:** Getting a high-level view of your Sline setup

---

### 📁 Projects

**URL:** http://localhost:3001/projects

**What It Does:** Manages project configurations

**Features:**
- **List Projects** - View all configured projects
- **Create Project** - Add new project with:
  - Name (e.g., `backend-api`)
  - Description (helps LLM classification)
  - Repository URL
  - Default branch
  - Slack Channel ID (optional)
- **Edit Project** - Update project settings
- **Delete Project** - Remove project and associated conversations

**Example Project:**
```yaml
Name: backend-api
Description: Python FastAPI backend handling authentication
Repo URL: https://github.com/mycompany/backend.git
Branch: main
Channel: C01ABC123 (optional)
```

**Use When:**
- Setting up new codebases for Sline to work with
- Updating repository URLs or branches
- Managing multi-project configurations

---

### 🧪 Admin Panel

**URL:** http://localhost:3001/admin

**What It Does:** Test Sline without Slack setup

**This is your most important testing tool!** 🌟

**Features:**
- **Project Selection** - Choose which project to query
- **Message Input** - Type your message to Sline
- **Send Button** - Trigger the agent
- **Response Display** - See Sline's response in real-time

**How It Works:**
```
Admin Panel
    ↓
Simulates Slack @mention
    ↓
Calls AgentService directly
    ↓
Creates/continues conversation
    ↓
Returns AI response
```

**Example Workflow:**
1. Select project: `my-project`
2. Enter message: `"What files are in the src/ directory?"`
3. Click "Send"
4. See response: "Hey! Looking at the src/ directory..."

**Use When:**
- Testing before Slack deployment
- Debugging agent behavior
- Validating project configuration
- Quick iteration during development

---

### ⚙️ Settings

**URL:** http://localhost:3001/settings

**What It Does:** Configure LLM provider credentials

**Features:**
- **Provider Selection:**
  - Anthropic (Claude)
  - OpenAI (GPT)
  - OpenRouter (multi-model)
  - Google Gemini
  - xAI (Grok)
  - Ollama (local)
  - OpenAI-Compatible (Azure, etc.)
- **API Key Input** (securely masked)
- **Model ID** (e.g., `claude-sonnet-4-5-20250929`)
- **Base URL** (optional, for compatible providers)
- **Provider Documentation** links

**⚠️ Important:** 
After saving settings, you **must restart the backend:**
```powershell
docker-compose restart backend
```

**Security Note:** API keys are stored in `backend/.env` file. Never commit this file to version control!

**Use When:**
- Initial setup
- Changing LLM providers
- Updating API keys
- Testing different models

---

## 🔄 Typical Workflows

### Workflow 1: First-Time Setup

```
1. Start services (docker-compose up)
2. Open Dashboard (localhost:3001)
3. Go to Settings → Configure API keys
4. Restart backend
5. Go to Projects → Create first project
6. Go to Admin Panel → Test conversation
7. Success! ✅
```

### Workflow 2: Testing New Feature

```
1. Make code changes to backend
2. FastAPI auto-reloads (no restart needed)
3. Go to Admin Panel
4. Test with sample message
5. Check backend logs for debugging
6. Iterate until working
```

### Workflow 3: Debugging Issues

```
1. Admin Panel → Try to reproduce issue
2. Check browser console (F12)
3. Check backend logs (docker-compose logs -f backend)
4. Check database (psql queries)
5. Fix issue
6. Retry in Admin Panel
```

### Workflow 4: Multi-Project Testing

```
1. Projects → Create Project A (backend)
2. Projects → Create Project B (frontend)
3. Admin Panel → Ask backend question
   - "Where is the authentication logic?"
   - Should select Project A
4. Admin Panel → Ask frontend question  
   - "Where is the login button?"
   - Should select Project B
5. Check logs to verify correct classification
```

---

## 🎨 Dashboard vs Slack

### Dashboard (Development)
- ✅ Fast iteration
- ✅ Easy debugging
- ✅ No Slack setup required
- ✅ Direct API testing
- ❌ No threading
- ❌ No team collaboration

### Slack (Production)
- ✅ Natural team conversations
- ✅ Thread-based context
- ✅ Multi-user collaboration
- ✅ Notifications
- ❌ Slower to test changes
- ❌ Requires Slack app setup

**Recommendation:** Use Dashboard for development, Slack for production.

---

## 🐛 Debugging with Dashboard

### Check API Connectivity

```javascript
// Browser console
fetch('http://localhost:8000/health')
  .then(r => r.json())
  .then(console.log)

// Should return: {"status": "healthy"}
```

### Inspect Network Requests

1. Open DevTools (F12)
2. Go to Network tab
3. Send message in Admin Panel
4. Look for POST request to `/api/test/sline-chat`
5. Check request/response payloads

### View Database State

```powershell
docker-compose exec db psql -U postgres -d slack_cline

# View projects
SELECT id, name, description FROM projects;

# View conversations
SELECT channel_id, thread_ts, message_count, created_at 
FROM conversations 
ORDER BY created_at DESC;

# Exit
\q
```

### Monitor Backend Logs

```powershell
# Real-time logs
docker-compose logs -f backend

# Look for:
✅ "Selected project 'project-name'"
✅ "🔧 Tool call: list_files(...)"
✅ "💬 Agent response: ..."
❌ "Error: ..." (if something fails)
```

---

## 🎯 Admin Panel Deep Dive

### What Happens When You Click "Send"

1. **Frontend** sends POST to `/api/test/sline-chat`
2. **Backend** receives request:
   ```python
   {
     "channel_id": "test_channel",
     "text": "your message",
     "user_id": "test_user"
   }
   ```
3. **AgentService** processes:
   - Load/create conversation state
   - Classify project (if multiple)
   - Append user message to history
   - Invoke LangGraph workflow
   - Get AI response
   - Save updated state
4. **Response** returned to frontend
5. **Display** in Admin Panel

### Multi-Turn Conversations

The Admin Panel supports conversation continuity:

```
First message: "What files are here?"
→ Creates conversation with thread_ts

Second message: "Can you read the README?"
→ Uses same thread_ts, sees full history

Third message: "What does it say?"
→ Sees all previous messages
```

Each conversation is identified by `(channel_id, thread_ts)` pair.

---

## 📊 Dashboard API Endpoints

The dashboard uses these REST APIs:

### Projects
```http
GET    /api/projects          # List all projects
POST   /api/projects          # Create project
PUT    /api/projects/{id}     # Update project
DELETE /api/projects/{id}     # Delete project
```

### Configuration
```http
GET  /api/config/api-keys     # Get config (masked)
POST /api/config/api-keys     # Update config
```

### Testing
```http
POST /api/test/sline-chat     # Test agent directly
```

### Health
```http
GET /api/health               # Dashboard API health
GET /health                   # Backend health
```

---

## 🔧 Configuration Files

### Frontend (.env)
```bash
# frontend/.env
VITE_API_URL=http://localhost:8000
```

### Backend (.env)
```bash
# backend/.env
CLINE_PROVIDER=anthropic
CLINE_API_KEY=sk-ant-...
CLINE_MODEL_ID=claude-sonnet-4-5-20250929

DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/slack_cline

SLACK_BOT_TOKEN=xoxb-... (optional for dashboard-only)
SLACK_SIGNING_SECRET=... (optional for dashboard-only)
```

---

## 🆘 Common Issues

### "Failed to load projects"

**Symptoms:** Projects page shows error

**Causes:**
- Backend not running
- CORS misconfigured
- Database connection failed

**Solutions:**
```powershell
# Check backend
curl http://localhost:8000/health

# Check database
docker-compose ps db

# Restart services
docker-compose restart backend
```

### "No response from agent"

**Symptoms:** Admin Panel hangs or times out

**Causes:**
- No API key configured
- Invalid project configuration
- LLM API error

**Solutions:**
1. Check Settings page - API key set?
2. Check backend logs for errors
3. Verify API key is valid
4. Restart backend after config changes

### "Project not found"

**Symptoms:** "No projects configured" error

**Solutions:**
1. Go to Projects page
2. Create at least one project
3. Refresh Admin Panel

### Frontend won't start

**Symptoms:** `npm run dev` fails

**Solutions:**
```powershell
# Clear node_modules
rm -r node_modules
npm install

# Check port 3001 is free
netstat -ano | findstr :3001

# Try different port
# Edit vite.config.ts: server: { port: 3002 }
```

---

## 💡 Pro Tips

### 1. Keep Backend Logs Open

```powershell
# Terminal 1: Services
docker-compose up

# Terminal 2: Logs
docker-compose logs -f backend
```

### 2. Use Browser DevTools

- **Console** - Check for JavaScript errors
- **Network** - Inspect API requests
- **Application** - View localStorage/cookies

### 3. Test Multi-Project Classification

Create 2+ projects with distinct descriptions, then ask questions that clearly belong to one:
- "Where is the authentication code?" → backend
- "Where is the login button?" → frontend

### 4. Monitor Database

Keep a psql session open:
```powershell
docker-compose exec db psql -U postgres -d slack_cline
# Run queries as needed
```

### 5. Quick Reset

To start fresh:
```powershell
docker-compose down -v  # WARNING: Deletes all data!
docker-compose up
# Reconfigure via dashboard
```

---

## 🚀 Next Steps

- **[Slack Usage Guide](slack-usage.md)** - Deploy to production Slack
- **[Troubleshooting](troubleshooting.md)** - Solve common problems
- **[Architecture Overview](../architecture/overview.md)** - Understand how it works

---

## 📚 Related Documentation

- **[Quick Start](../getting-started/quickstart.md)** - Initial setup guide
- **[Development Setup](../development/setup.md)** - Local dev environment
- **[API Reference](../development/api-reference.md)** - REST API docs

---

**Questions?** Check the [Troubleshooting Guide](troubleshooting.md) or [open an issue](https://github.com/your-org/sline/issues).
