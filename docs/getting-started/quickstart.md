# Quick Start Guide

Get Sline up and running in 5 minutes! 🚀

## What You'll Build

A working Sline instance that you can test via:
1. **Dashboard** - Web interface for testing (recommended for first-time setup)
2. **Slack** - Production @mention-based interaction

## Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for dashboard only)
- LLM API key (Anthropic, OpenAI, or OpenRouter)
- Slack workspace (for production use, optional for testing)

---

## Step 1: Start Backend Services (2 minutes)

```powershell
cd slack-cline

# Start PostgreSQL and backend
docker-compose up
```

**Expected output:**
```
✅ backend-1  | INFO:     Application startup complete
✅ db-1       | database system is ready to accept connections
```

Backend is now running at **http://localhost:8000**

---

## Step 2: Start Dashboard (1 minute)

Open a **new terminal**:

```powershell
cd slack-cline/frontend

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev
```

Dashboard will be available at **http://localhost:3001**

---

## Step 3: Configure API Keys (1 minute)

1. Open **http://localhost:3001/settings**
2. Select your LLM provider (e.g., Anthropic)
3. Enter your API key
4. Enter model ID (e.g., `claude-sonnet-4-5-20250929`)
5. Click **Save Configuration**

**⚠️ Important:** Restart the backend after saving:
```powershell
docker-compose restart backend
```

---

## Step 4: Create a Project (1 minute)

1. Open **http://localhost:3001/projects**
2. Click **+ New Project**
3. Fill in:
   - **Name**: `my-first-project`
   - **Description**: `Test project for learning Sline`
   - **Repository URL**: `https://github.com/your-username/your-repo.git`
   - **Default Branch**: `main`
4. Click **Create**

> **Note:** For testing, you can use any public GitHub repo. The workspace will be created but not actually cloned in MVP.

---

## Step 5: Test with Dashboard (< 1 minute)

1. Open **http://localhost:3001/admin**
2. Your project should appear in the dropdown
3. Enter a message: **"What files are in this project?"**
4. Click **Send**
5. Watch Sline respond! 🎉

**What happens:**
- Sline creates a conversation
- Uses the `list_files` tool automatically
- Responds with file listing
- State is saved to database

---

## ✅ Success! What's Next?

### Test Multi-Turn Conversations

Try asking follow-up questions:
```
1. "What files are in this project?"
2. "Can you read the README?"
3. "Search for TODO comments"
```

Sline remembers the full conversation history!

### Check the Database

```powershell
docker-compose exec db psql -U postgres -d slack_cline

# View conversations
SELECT channel_id, thread_ts, project_id, message_count FROM conversations;

# View projects
SELECT name, description FROM projects;

# Exit
\q
```

### View Backend Logs

```powershell
docker-compose logs -f backend

# Look for:
# "Selected project 'my-first-project'"
# "🔧 Tool call: list_files(...)"
# "💬 Agent response: ..."
```

---

## 🚀 Next Steps

### For Dashboard Testing
- **[Dashboard Guide](../user-guide/dashboard.md)** - Learn all dashboard features
- **[User Guide](../user-guide/slack-usage.md)** - Understand @mention patterns

### For Slack Integration
- **[Slack Setup](../user-guide/slack-usage.md#slack-app-setup)** - Configure production Slack app
- **Create multiple projects** - Test LLM project classification

### For Development
- **[Development Setup](../development/setup.md)** - Set up local dev environment
- **[Architecture Overview](../architecture/overview.md)** - Understand how it works

---

## 🆘 Troubleshooting

### "Failed to load projects"

**Issue:** Frontend can't reach backend

**Solution:**
```powershell
# Check backend is running
curl http://localhost:8000/health

# Restart backend
docker-compose restart backend

# Check CORS is configured (should allow localhost:3001)
docker-compose logs backend | grep CORS
```

### "No projects configured"

**Issue:** Database is empty

**Solution:** Create a project via Dashboard Projects page or API

### "Configuration error"

**Issue:** API keys not set

**Solution:**
1. Go to Settings page
2. Enter API key and model
3. **Restart backend**: `docker-compose restart backend`

### Backend won't start

**Check logs:**
```powershell
docker-compose logs backend

# Common issues:
# - Port 8000 already in use
# - Missing environment variables
# - Database connection failed
```

**Solution:** Ensure `.env` file exists with correct DATABASE_URL

---

## 🎯 What You've Accomplished

✅ **Running Services**
- PostgreSQL database
- FastAPI backend with LangGraph agent
- React dashboard

✅ **Configured**
- LLM provider credentials
- Project repository mapping

✅ **Tested**
- Conversational AI agent
- Autonomous tool usage
- State persistence

---

## 💡 Pro Tips

### Use Admin Panel for Development

The Admin Panel (`/admin`) is your best friend for:
- Testing new features
- Debugging issues
- Validating before Slack deployment

### Monitor Conversations

Check database regularly:
```sql
SELECT 
  channel_id, 
  thread_ts, 
  message_count,
  created_at 
FROM conversations 
ORDER BY created_at DESC;
```

### Hot Reload

Edit Python files and FastAPI auto-reloads - no restart needed!

### Clean Slate

To reset everything:
```powershell
docker-compose down -v  # Deletes database!
docker-compose up
```

---

## 📚 Learn More

- **[Architecture Overview](../architecture/overview.md)** - How Sline works internally
- **[Agent System](../architecture/agent-system.md)** - LangGraph and SlineBrain details
- **[Multi-Project Setup](../architecture/multi-project.md)** - LLM classification

---

**Got questions?** Check the [Troubleshooting Guide](../user-guide/troubleshooting.md) or [open an issue](https://github.com/your-org/sline/issues).

**Ready to use Sline in Slack?** → [Slack Setup Guide](../user-guide/slack-usage.md)
