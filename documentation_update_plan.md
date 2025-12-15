# Documentation Update Implementation Plan

## [Overview]

Update Sline documentation to accurately reflect the current dashboard implementation, new features (Integrations, Settings tabs, Rules, MCP servers), and remove references to outdated concepts (Runs page, RunModel).

The Sline dashboard has evolved significantly beyond its initial design documented in `docs/user-guide/dashboard.md`. The current implementation includes a modern home dashboard with GitHub project cards and monitoring charts, a comprehensive Integrations hub, a 4-tab Settings page (Providers, Agent, MCP Servers, Advanced), and project-per-workspace rules management. The existing documentation references outdated concepts like a dedicated "Runs" page (now replaced with conversation-based tracking) and doesn't cover new features that are central to the user experience.

This update will ensure all documentation accurately reflects the production codebase, helping new users understand the actual capabilities and workflows of Sline.

## [Types]

No new TypeScript types or data structures are required for this documentation update.

This is purely a documentation task - all necessary types already exist in `frontend/src/types/index.ts` including `Project`, `Run`, `AgentConfig`, etc. The documentation will describe how these existing types are used in the dashboard UI.

## [Files]

Documentation files that need to be updated or created.

### Files to Update:

1. **docs/user-guide/dashboard.md** - Complete rewrite
   - Current: References outdated "Runs" page, missing new features
   - Update to: Cover Dashboard home, Integrations hub, 4-tab Settings page, Admin Panel workflow
   
2. **docs/README.md** - Fix broken links
   - Current: Links to non-existent files (`slack-usage.md`, `troubleshooting.md`, `setup.md`, `api-reference.md`, `contributing.md`)
   - Update to: Remove/comment out links to TODO pages, keep only existing docs

3. **docs/getting-started/quickstart.md** - Minor updates
   - Current: Mostly accurate but references outdated Settings structure
   - Update to: Reflect 4-tab Settings page (Providers, Agent, MCP, Advanced)

### Files to Create:

4. **docs/user-guide/integrations.md** - NEW
   - Purpose: Document the Integrations hub page
   - Content: MCP servers management, Rules tab (project-specific .clinerules), future API integrations

5. **docs/user-guide/conversations.md** - NEW  
   - Purpose: Document conversation-based model vs old Run model
   - Content: Thread-based conversations, state persistence, Admin Panel testing

6. **docs/development/frontend-structure.md** - NEW
   - Purpose: Document frontend architecture for contributors
   - Content: React component structure, routing, API client usage

### Files to Archive/Deprecate:

7. **backend/models/run.py** - Add deprecation comment
   - Current: Still exists but unused in conversation model
   - Update: Add clear deprecation notice at top of file

8. **frontend/src/pages/Runs.tsx** - Add deprecation notice
   - Current: Legacy page that still renders but shows outdated data
   - Update: Add UI banner warning it's deprecated, link to Conversations docs

## [Functions]

No code changes or function modifications needed for this documentation task.

All existing functions in the codebase remain unchanged. The documentation will describe how existing functions and components work together (e.g., `apiClient.getProjects()`, `AgentService.handle_message()`, etc.).

## [Classes]

No class modifications needed for this documentation task.

Existing database models (`ConversationModel`, `ProjectModel`, `RunModel`) and service classes (`AgentService`, `DashboardService`) remain unchanged. Documentation will describe their roles and relationships.

## [Dependencies]

No new dependencies required for documentation updates.

All documentation will be written in Markdown format using the existing docs structure. No additional tools or packages needed.

## [Testing]

Testing approach for documentation accuracy.

### Verification Steps:

1. **Visual Inspection** - Open dashboard and verify each documented feature exists:
   - Dashboard home (project cards, monitor charts, quick actions)
   - Projects page CRUD operations
   - Integrations page (MCP servers, rules placeholders)
   - Admin Panel conversation testing
   - Settings 4-tab structure

2. **Link Testing** - Verify all internal documentation links work:
   - Check relative links between markdown files
   - Ensure referenced files exist
   - Test anchor links within pages

3. **Code Cross-Reference** - Verify documented API endpoints exist:
   - Check `backend/modules/dashboard/routes.py` for endpoints
   - Verify frontend `src/api/client.ts` matches described API calls
   - Confirm component names match actual files

4. **User Flow Testing** - Walk through documented workflows:
   - Follow quickstart guide step-by-step
   - Test dashboard guide instructions
   - Verify troubleshooting solutions work

### Test Files:

No automated tests needed for documentation. Manual review process:
- [ ] Read updated dashboard.md against live dashboard
- [ ] Click through all documentation links
- [ ] Follow quickstart guide from scratch
- [ ] Verify all code snippets are accurate

## [Implementation Order]

Logical sequence for updating documentation to minimize conflicts and ensure accuracy.

### Step 1: Audit Current State (15 min)
- [ ] Open dashboard at `http://localhost:3001` and screenshot each page
- [ ] List all actual features per page (Dashboard, Projects, Integrations, Admin, Settings)
- [ ] Note Settings tab names (Providers, Agent, MCP Servers, Advanced)
- [ ] Check which docs files exist vs referenced in README.md

### Step 2: Update Core User-Facing Docs (60 min)
- [ ] Rewrite `docs/user-guide/dashboard.md` with accurate sections:
  - Dashboard Home (project cards with GitHub stats, Monitor charts)
  - Projects page (CRUD operations)
  - Integrations page (MCP servers hub)
  - Admin Panel (conversation testing)
  - Settings (4 tabs breakdown)
- [ ] Create `docs/user-guide/integrations.md` (MCP servers, rules)
- [ ] Create `docs/user-guide/conversations.md` (conversation model explanation)

### Step 3: Update Getting Started Guide (20 min)
- [ ] Update `docs/getting-started/quickstart.md`:
  - Fix Settings section to mention 4 tabs
  - Update screenshots references if needed
  - Verify all steps still accurate

### Step 4: Fix Documentation Index (15 min)
- [ ] Update `docs/README.md`:
  - Remove/comment broken links (slack-usage.md, troubleshooting.md, etc.)
  - Add new files (integrations.md, conversations.md)
  - Reorganize "What's Available" vs "Coming Soon" sections

### Step 5: Add Developer Documentation (30 min)
- [ ] Create `docs/development/frontend-structure.md`:
  - Component hierarchy (AppShell > Sidebar + Routes)
  - Page components (Dashboard, Projects, Integrations, Settings, Admin, Docs)
  - API client usage patterns
  - Settings tabs architecture

### Step 6: Deprecation Notices (10 min)
- [ ] Add deprecation comment to `backend/models/run.py`:
  ```python
  # DEPRECATED: RunModel is legacy from CLI-based architecture.
  # Current implementation uses ConversationModel (conversation.py).
  # This file kept for backwards compatibility only.
  ```
- [ ] Add UI deprecation banner to `frontend/src/pages/Runs.tsx`:
  - Alert box at top: "This page is deprecated. See Conversations model instead."

### Step 7: Review and Cross-Reference (20 min)
- [ ] Read each updated doc file against live dashboard
- [ ] Test all inter-doc links
- [ ] Verify code examples match actual API
- [ ] Check for consistency in terminology (conversation vs run)

### Step 8: Update Migration Document (10 min)
- [ ] Update `docs/DOCUMENTATION_MIGRATION.md` with this round of changes
- [ ] Add section "December 2024 - Dashboard Feature Update"
- [ ] List files changed and reasons

---

## Detailed Content Outlines

### docs/user-guide/dashboard.md (REWRITE)

```markdown
# Dashboard Guide

The Sline Dashboard is your central hub for managing your AI coding agent, configuring projects, testing conversations, and managing integrations.

**Dashboard URL:** http://localhost:3001

## Dashboard Pages

### 🏠 Home Dashboard
Your landing page with an overview of projects and activity monitoring.

**Features:**
- **GitHub Project Cards** - Visual cards showing:
  - Project name and description
  - Repository link with external icon
  - GitHub stats (stars, forks, language)
  - Last updated time
- **Monitor Section** - Track agent activity:
  - Toggle between Runs and Cost metrics
  - Time range selector (7/30/90 days)
  - Project filter dropdown
  - Area chart visualization with totals
- **Quick Actions** - Shortcuts to:
  - Manage Projects
  - Test Integration (Admin Panel)
  - Configure API Keys (Settings)

### 📁 Projects
Manage your code repositories and project configurations.

**Features:**
- **Project List** - All configured projects
- **Create Project** - Add new repository with:
  - Name (e.g., `backend-api`)
  - Description (helps AI classify questions)
  - Repository URL
  - Default branch
  - Slack channel ID (optional)
- **Edit/Delete** - Modify existing projects

**Use When:** Setting up new codebases for Sline to work with

### 🧩 Integrations
Central hub for extending Sline's capabilities.

**Features:**
- **MCP Servers Tab** - Model Context Protocol servers
  - Add filesystem, Git, HTTP, database servers
  - Configure authentication
  - Empty state with helpful guidance
- **Rules Tab** (Coming Soon) - Per-project .clinerules
- **APIs Tab** (Coming Soon) - External service integrations

**Use When:** Adding tools and capabilities to your agent

### 🧪 Admin Panel
Test Sline's conversational AI without Slack setup.

**Features:**
- **Project Selector** - Choose which project to query
- **Message Input** - Type your question/request
- **Send Button** - Trigger the agent
- **Response Display** - See AI response in real-time
- **Conversation Continuity** - Multi-turn conversations with memory

**Use When:** Testing before Slack deployment, debugging agent behavior

### ⚙️ Settings
Configure LLM providers, agent behavior, MCP servers, and advanced options.

**Settings Tabs:**
1. **Providers Tab**
   - Select LLM provider (Anthropic, OpenAI, OpenRouter, etc.)
   - Enter API key
   - Configure model ID
   - Optional base URL for compatible providers

2. **Agent Tab**
   - Agent persona/system prompt
   - Autonomy settings (file writes, shell commands)
   - Approval requirements
   - Default temperature and max tokens

3. **MCP Servers Tab**
   - Manage MCP server configurations
   - Same content as Integrations > MCP Servers
   - Quick access from settings context

4. **Advanced Tab**
   - Debug settings
   - System configuration
   - Feature flags

**Important:** Restart backend after changing API keys!

### 📚 Docs
In-app documentation browser (this documentation!).

**Features:**
- Sidebar navigation with sections
- Markdown rendering
- Syntax highlighting
- Responsive layout
- Separate from main app shell for custom layout

## Workflows

### First-Time Setup
1. Dashboard → Settings → Providers → Configure API key
2. Restart backend: `docker-compose restart backend`
3. Projects → Create project
4. Admin Panel → Test conversation
5. Success! ✅

### Testing New Feature
1. Make code changes to backend
2. FastAPI auto-reloads (no restart needed)
3. Admin Panel → Test with sample message
4. Check backend logs for debugging
5. Iterate

### Debugging Issues
1. Admin Panel → Try to reproduce issue
2. Browser DevTools (F12) → Check console
3. Backend logs → `docker-compose logs -f backend`
4. Database → `psql -U postgres -d slack_cline`
5. Fix and retry

## Dashboard vs Slack

| Dashboard (Development) | Slack (Production) |
|-------------------------|-------------------|
| ✅ Fast iteration | ✅ Team collaboration |
| ✅ Easy debugging | ✅ Thread-based context |
| ✅ No Slack setup needed | ✅ Notifications |
| ❌ No threading | ❌ Slower to test |

**Recommendation:** Use Dashboard for development, Slack for production.
```

### docs/user-guide/integrations.md (NEW)

```markdown
# Integrations Guide

Extend Sline's capabilities with MCP servers, custom rules, and API integrations.

## MCP Servers

Model Context Protocol servers provide additional tools and data sources for your agent.

### Server Types

- **Filesystem** - Read/write files in specific directories
- **Git** - Interact with Git repositories
- **HTTP** - Make API calls to external services
- **Database** - Query and modify database records
- **Custom** - Build your own integration

### Adding an MCP Server

1. Go to Integrations → MCP Servers
2. Click "Add MCP Server"
3. Configure:
   - Server name
   - Type (filesystem/git/http/database/custom)
   - Endpoint/URL
   - Authentication method
4. Save and test connection

### Example: Filesystem Server

```json
{
  "name": "Project Workspace",
  "type": "filesystem",
  "endpoint": "/data/workspaces",
  "auth_method": "none"
}
```

## Rules (Coming Soon)

Per-project .clinerules for customizing agent behavior.

### What are Rules?

Rules are project-specific instructions that customize how Sline behaves for different codebases:

- Code style preferences
- Testing requirements
- Deployment workflows
- Team conventions

### Rules Structure

```
project-root/
└── .clinerules/
    ├── code-style.md
    ├── testing.md
    └── deployment.md
```

## API Integrations (Coming Soon)

Connect external services:
- Issue trackers (Jira, Linear)
- CI/CD systems (GitHub Actions, GitLab CI)
- Monitoring (Datadog, Sentry)
```

### docs/user-guide/conversations.md (NEW)

```markdown
# Conversations Guide

Understanding Sline's conversation-based model.

## Conversation Model

Sline uses a **conversation-based** approach, not a "run" or "task" model.

### Key Concepts

**One Thread = One Conversation**
- Each Slack thread is a persistent conversation
- State is saved to PostgreSQL
- Survives server restarts
- Multi-turn interactions with memory

**Conversation State**
- Full message history
- Workspace path
- Project context
- Mode (chat/planning/executing)
- File cache

### Conversation Lifecycle

1. **User @mentions Sline** in Slack
2. **Backend creates conversation** (channel_id, thread_ts)
3. **Agent processes message** with tools
4. **State is saved** to database
5. **User replies in thread**
6. **Conversation continues** with full context

### vs. Old Run Model

| Conversation Model (Current) | Run Model (Deprecated) |
|------------------------------|------------------------|
| Thread-based, persistent | Task-based, ephemeral |
| Multi-turn with memory | Single execution |
| Slack-native UX | CLI-based concepts |
| ConversationModel table | RunModel table (legacy) |

### Testing Conversations

Use the Admin Panel to test conversation flow:

1. Select project
2. Send message: "What files are here?"
3. Agent responds with list_files output
4. Send follow-up: "Read the README"
5. Agent remembers context from step 2 ✅

### Database Structure

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    channel_id VARCHAR,
    thread_ts VARCHAR,  -- Slack thread timestamp
    project_id UUID,
    state_json JSON,    -- Serialized conversation state
    message_count INT,
    UNIQUE(channel_id, thread_ts)
);
```
```

## [Dependencies]

None required - pure documentation task.

## [Testing]

Manual verification against live dashboard as described in Testing section above.

---

## Summary

This plan updates documentation to match the current Sline implementation:
- ✅ Rewrite dashboard.md to cover Home, Projects, Integrations, Admin, Settings (4 tabs)
- ✅ Create integrations.md for MCP servers and rules
- ✅ Create conversations.md to explain conversation model vs runs
- ✅ Fix broken links in README.md
- ✅ Update quickstart.md for 4-tab Settings
- ✅ Add deprecation notices to Run-related code
- ✅ Create frontend-structure.md for developers

**Estimated Time:** 3 hours total
**Files Changed:** 8 documentation files
**New Files:** 3 (integrations.md, conversations.md, frontend-structure.md)
