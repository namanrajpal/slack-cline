# Multi-Project LLM Classification Implementation

## Overview

Sline now uses **LLM-based classification** to intelligently determine which project you're asking about, rather than being limited to channel-specific mappings.

## What Changed

### 1. Project Model Updated
```python
# OLD (Channel-locked)
class ProjectModel:
    slack_channel_id: str  # Required - locks project to one channel
    repo_url: str

# NEW (Multi-project aware)
class ProjectModel:
    name: str                  # e.g., "backend-api"
    description: str           # e.g., "Python FastAPI authentication service"
    slack_channel_id: Optional[str]  # Optional now
    repo_url: str
```

### 2. LLM Classifier Added
```python
# backend/modules/agent/classifier.py
async def classify_project(user_question, projects, llm_model):
    """
    Analyzes user question and project descriptions to select
    the most relevant project automatically.
    """
```

### 3. AgentService Updated
```python
# OLD: Look up by channel
project = await get_project_for_channel(channel_id)

# NEW: Classify from all projects
all_projects = await get_all_projects()
project = await classify_project(user_question, all_projects, llm)
```

## How It Works

### Example: Two Projects Configured

**Project 1:**
- Name: `backend-api`
- Description: "Python FastAPI backend handling authentication and user management"
- Repo: github.com/company/backend

**Project 2:**
- Name: `frontend-web`
- Description: "React TypeScript frontend with Tailwind CSS"
- Repo: github.com/company/frontend

### Conversation Flow

```
User: "What files handle user login?"

Sline (internally):
1. Load all projects
2. Ask LLM: "User asks about 'user login'. Which project?
   1. backend-api: Python FastAPI auth...
   2. frontend-web: React TypeScript..."
3. LLM responds: "1" (backend-api)
4. Load workspace for backend-api
5. Use tools to search for login code
6. Answer: "In backend-api, login is handled in auth/login.py..."

User: "Show me the login button component"

Sline (internally):
1. Load all projects  
2. Ask LLM: "User asks about 'login button component'. Which project?
   1. backend-api: Python FastAPI...
   2. frontend-web: React TypeScript..."
3. LLM responds: "2" (frontend-web - UI components)
4. Load workspace for frontend-web
5. Search for LoginButton component
6. Answer: "In frontend-web, found LoginButton.tsx..."
```

## Database Migration Required

The Project schema changed, so you need to recreate the database:

```powershell
# Stop services
docker-compose down

# Remove old database (WARNING: deletes all data)
docker-compose down -v

# Restart with new schema
docker-compose up
```

## Creating Projects (New UI)

### Via Dashboard

**Projects Page** → "+ New Project"

**Required Fields:**
- **Name**: `backend-api` (unique identifier)
- **Description**: "Python FastAPI backend for authentication" (helps LLM classify)
- **Repository URL**: `https://github.com/company/backend.git`
- **Default Branch**: `main`

**Optional:**
- **Slack Channel ID**: Can still link to specific channel if desired

### Via API

```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "backend-api",
    "description": "Python FastAPI backend for authentication and user management",
    "repo_url": "https://github.com/company/backend.git",
    "default_ref": "main"
  }'
```

## Testing the Classifier

### Test 1: Single Project (No Classification)
```bash
# Create one project
curl -X POST http://localhost:8000/api/projects \
  -d '{"name": "test-proj", "description": "Test project", "repo_url": "https://github.com/test/repo.git"}'

# Ask question
curl -X POST http://localhost:8000/api/test/sline-chat \
  -d '{"channel_id": "C123", "text": "What files are there?", "user_id": "U123"}'

# Should use test-proj automatically
```

### Test 2: Multiple Projects (Classification)
```bash
# Create backend project
curl -X POST http://localhost:8000/api/projects \
  -d '{"name": "backend-api", "description": "Python backend with auth", "repo_url": "https://github.com/test/backend.git"}'

# Create frontend project
curl -X POST http://localhost:8000/api/projects \
  -d '{"name": "frontend-web", "description": "React frontend UI", "repo_url": "https://github.com/test/frontend.git"}'

# Ask backend question
curl -X POST http://localhost:8000/api/test/sline-chat \
  -d '{"channel_id": "C123", "text": "What files handle database connections?", "user_id": "U123"}'
# Should classify to backend-api

# Ask frontend question
curl -X POST http://localhost:8000/api/test/sline-chat \
  -d '{"channel_id": "C123", "text": "Where is the login button component?", "user_id": "U123"}'
# Should classify to frontend-web
```

### Check Logs for Classification

```bash
docker-compose logs backend | grep "Selected project"

# You should see:
# "Selected project 'backend-api' for conversation..."
# "Selected project 'frontend-web' for conversation..."
```

## Benefits

✅ **No more channel mapping** - Ask about any project from anywhere
✅ **Intelligent routing** - LLM understands your intent
✅ **Cross-project queries** - "Which project has the login code?"
✅ **Flexible organization** - Add/remove projects without channel constraints

## Frontend UI Update (Phase 2)

The Projects page needs UI updates to:
1. Replace "Channel ID" field with "Name" field
2. Add "Description" textarea
3. Make "Channel ID" optional (advanced settings)

This will be implemented after backend testing is complete.

## Next Steps

1. **Recreate database**: `docker-compose down -v && docker-compose up`
2. **Create test projects** with names and descriptions
3. **Test classification** with backend vs frontend questions
4. **Monitor logs** to verify correct project selection
5. **Update frontend** Projects page (Phase 2)
