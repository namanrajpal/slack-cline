# Dashboard Guide

The Sline Dashboard is your **central hub** for managing your AI coding agent, configuring projects, testing conversations, and managing integrations.

**Dashboard URL:** http://localhost:3001

---

## 🎯 Dashboard Purpose

The dashboard serves as your development and configuration interface:

1. **Development & Testing** - Test Sline's agent without Slack setup
2. **Project Management** - Configure repositories and workspaces
3. **Configuration** - Manage LLM providers, agent settings, MCP servers
4. **Monitoring** - Track agent activity and costs

> **Key Principle:** Dashboard is for development/testing. Slack is the production interface.

---

## 📊 Dashboard Pages

### 🏠 Home Dashboard

**URL:** http://localhost:3001

Your landing page with project overview and activity monitoring.

#### Features

**GitHub Project Cards** - Visual cards for each configured project:
- Project name and description
- Repository URL with external link icon
- Live GitHub stats (⭐ stars, 🍴 forks, language)
- Last updated timestamp
- Hover effects and direct repo links

**Monitor Section** - Track agent activity with interactive charts:
- **Metric Toggle**: Switch between Runs and Cost views
- **Time Range**: 7, 30, or 90-day windows
- **Project Filter**: View all projects or filter by specific one
- **Area Chart**: Beautiful visualization with:
  - Total metrics (sum across time period)
  - Average per day
  - Trend indicator (+12% change)
  - Gradient fills and responsive layout

**Quick Actions** - Fast navigation shortcuts:
- **Manage Projects** → Projects page
- **Test Integration** → Admin Panel
- **Configure API Keys** → Settings page

#### Use When
- Getting a high-level overview of your setup
- Quick access to common tasks
- Monitoring agent usage patterns

---

### 📁 Projects

**URL:** http://localhost:3001/projects

Manage your code repositories and project configurations.

#### Features

**Project List** - View all configured projects with:
- Project name and description
- Repository URL
- Edit and delete actions

**Create Project** - Add new repository:
- **Name**: Identifier (e.g., `backend-api`, `frontend-app`)
- **Description**: Helps LLM classification ("Python FastAPI backend handling auth")
- **Repository URL**: GitHub/GitLab repo URL
- **Default Branch**: Usually `main` or `develop`
- **Slack Channel ID** (optional): Link to specific Slack channel

**Edit/Delete** - Modify existing projects or remove them

#### Example Project

```yaml
Name: backend-api
Description: Python FastAPI backend handling authentication and user management
Repo URL: https://github.com/mycompany/backend.git
Branch: main
Channel: C01ABC123 (optional)
```

#### Use When
- Setting up new codebases for Sline
- Updating repository URLs or branches
- Managing multi-project configurations

---

### 🧩 Integrations

**URL:** http://localhost:3001/integrations

Central hub for extending Sline's capabilities with external tools and services.

#### Current Features

**MCP Servers Tab** - Model Context Protocol servers:
- Add filesystem, Git, HTTP, database, or custom servers
- Configure server endpoints and authentication
- Test connections
- Empty state with helpful setup guidance

**Backend Integration Note**: Currently MCP server management uses localStorage. Backend endpoint `/api/mcp-servers` needs implementation for persistence.

#### Coming Soon

- **Rules Tab**: Per-project `.clinerules` management
- **APIs Tab**: External service integrations (Jira, Linear, CI/CD)

#### Use When
- Adding tools and capabilities to your agent
- Configuring filesystem access or database connections
- Setting up custom integrations

---

### 🧪 Admin Panel

**URL:** http://localhost:3001/admin

**This is your most important testing tool!** 🌟

Test Sline's conversational AI without Slack setup.

#### Features

**Project Selection** - Dropdown to choose which project to query

**Message Input** - Text area for your question/request

**Send Button** - Triggers the agent

**Response Display** - Real-time AI response with:
- Formatted markdown
- Code syntax highlighting
- Tool call visibility

**Conversation Continuity** - Multi-turn conversations with full memory

#### How It Works

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

#### Example Workflow

1. Select project: `my-project`
2. Enter message: `"What files are in the src/ directory?"`
3. Click "Send"
4. See response: "Hey! Looking at the src/ directory..."
5. Follow-up: "Can you read the main.py file?"
6. Agent remembers context from previous messages ✅

#### Use When
- Testing before Slack deployment
- Debugging agent behavior
- Validating project configuration
- Quick iteration during development

---

### ⚙️ Settings

**URL:** http://localhost:3001/settings

Configure LLM providers, agent behavior, MCP servers, and advanced options.

Sline Settings is organized into **4 tabs**:

#### 1. Providers Tab

Configure your LLM provider and credentials.

**Features:**
- **Provider Selection**: Anthropic, OpenAI, OpenRouter, Google Gemini, xAI, Ollama, OpenAI-Compatible
- **API Key Input**: Securely masked key entry
- **Model ID**: e.g., `claude-sonnet-4-5-20250929`, `gpt-4`
- **Base URL** (optional): For compatible providers like Azure OpenAI
- **Provider Documentation**: Links to setup guides

**⚠️ Important:** After saving settings, you **must restart the backend**:
```powershell
docker-compose restart backend
```

**Security Note:** API keys are stored in `backend/.env`. Never commit this file!

#### 2. Agent Tab

Customize agent behavior and autonomy.

**Features:**
- **Agent Persona**: System prompt defining personality and behavior
- **Autonomy Settings**:
  - Allow file writes (create/modify/delete files)
  - Allow shell commands (execute terminal commands)
  - Require approval for large plans
- **Default Settings**:
  - Max concurrent tasks (1-10)
  - Temperature (0.0-2.0)
  - Max tokens (output length limit)

**Backend Integration Note**: Currently uses localStorage. Backend endpoint `/api/config/agent` needs implementation.

#### 3. MCP Servers Tab

Manage Model Context Protocol server configurations.

Same content as **Integrations → MCP Servers**, but accessible from Settings context for convenience.

**Features:**
- Add/edit/delete MCP servers
- Configure authentication
- Test connections

#### 4. Advanced Tab

System-level configuration and debugging options.

**Features:**
- Debug settings
- Feature flags
- System configuration options

---

### 📚 Docs

**URL:** http://localhost:3001/docs

In-app documentation browser (you're reading this now!).

#### Features

- **Sidebar Navigation**: Organized by section (Getting Started, User Guide, Architecture, Development)
- **Markdown Rendering**: Beautiful formatting with syntax highlighting
- **Responsive Layout**: Works on desktop and mobile
- **Separate Layout**: Custom layout independent of main app shell

#### Sections

- **Getting Started**: Quickstart guide, installation
- **User Guide**: Dashboard, integrations, conversations, Slack usage
- **Architecture**: System design, agent workflow, multi-project classification
- **Development**: Setup, debugging, API reference, contributing

---

## 🔄 Typical Workflows

### Workflow 1: First-Time Setup

```
1. Start services (docker-compose up)
2. Open Dashboard (localhost:3001)
3. Go to Settings → Providers → Configure API keys
4. Restart backend (docker-compose restart backend)
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
2. Browser Console (F12) → Check for errors
3. Backend logs → docker-compose logs -f backend
4. Database → psql queries
5. Fix issue
6. Retry in Admin Panel
```

### Workflow 4: Multi-Project Testing

```
1. Projects → Create Project A (backend)
2. Projects → Create Project B (frontend)
3. Admin Panel → Ask backend question
   "Where is the authentication logic?"
   → Should select Project A
4. Admin Panel → Ask frontend question
   "Where is the login button?"
   → Should select Project B
5. Check logs to verify correct classification
```

---

## 🎨 Dashboard vs Slack

### Dashboard (Development)
✅ Fast iteration  
✅ Easy debugging  
✅ No Slack setup required  
✅ Direct API testing  
❌ No threading  
❌ No team collaboration  

### Slack (Production)
✅ Natural team conversations  
✅ Thread-based context  
✅ Multi-user collaboration  
✅ Notifications  
❌ Slower to test changes  
❌ Requires Slack app setup  

**Recommendation:** Use Dashboard for development, Slack for production.

---

## 🐛 Debugging with Dashboard

### Check API Connectivity

```javascript
// Browser console (F12)
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
     "user_id": "test_user",
     "project_id": "selected-project-uuid"
   }
   ```
3. **AgentService** processes:
   - Load/create conversation state
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
1. Check Settings → Providers - API key set?
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

- **[Integrations Guide](integrations.md)** - Set up MCP servers and rules
- **[Conversations Guide](conversations.md)** - Understand conversation model
- **[Slack Usage Guide](#)** - Deploy to production Slack (coming soon)
- **[Troubleshooting](#)** - Common problems and solutions (coming soon)

---

## 📚 Related Documentation

- **[Quick Start](../getting-started/quickstart.md)** - Initial setup guide
- **[Architecture Overview](../architecture/overview.md)** - How Sline works internally
- **[Development Setup](../development/debugging.md)** - Local dev environment

---

**Questions?** Open an issue on [GitHub](https://github.com/your-org/sline/issues) or check the troubleshooting guide.

**Ready to use Sline in Slack?** → Slack Setup Guide (coming soon)
