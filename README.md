# Sline - Your AI Coding Teammate in Slack

**Sline is a conversational AI coding assistant that lives in Slack, helping development teams understand their codebase, answer questions, and collaborate on implementation ideas.**

Simply @mention Sline anywhere in Slack, and it becomes part of the conversation - analyzing code, answering questions, and suggesting improvements naturally.

## 🎯 Product Vision

Sline isn't a bot you command - it's a teammate you collaborate with.

```
#frontend-team channel

👤 Alice: Hey team, we need to add dark mode. @sline what do you think?

🤖 Sline: Hey! 👋 Looking at the codebase, I see you're using Tailwind CSS 
         with a theme provider in `src/context/ThemeContext.tsx`. 
         
         Here's what I'd suggest:
         1. Add dark mode classes to your tailwind.config.js
         2. Update the ThemeContext to persist preference
         3. Add a toggle component

👤 Bob: We also need to make sure it respects system preferences

🤖 Sline: Good point Bob! I'll include `prefers-color-scheme` media query 
         detection. The ThemeContext can check this on mount.
```

## ✨ Key Features

- **💬 Conversational**: Just @mention Sline - no command syntax to learn
- **🧵 Thread-aware**: Maintains conversation context across multiple messages
- **🔧 Autonomous**: Uses tools (read files, search code) automatically when needed
- **💾 Persistent**: Conversations survive server restarts
- **🎯 Multi-project**: Intelligently selects the right project based on context
- **📊 Dashboard**: Test and configure without touching Slack

## 🏗️ Architecture

Sline uses a **native Python LangGraph agent** (no subprocess calls, no external CLI):

```
Slack @mentions → FastAPI Backend → SlineBrain (ReAct Agent)
                        ↓                   ↓
                   PostgreSQL         File Tools
                (Conversations)    (read/search/list)
```

- **SlineBrain**: LangGraph ReAct agent with autonomous tool usage
- **Conversations**: PostgreSQL stores thread state with full message history
- **Tools**: Bound to workspace (read_file, list_files, search_files)
- **Dashboard**: React app for testing and configuration

**See [FINAL_ARCHITECTURE.md](./FINAL_ARCHITECTURE.md) for complete architecture details.**

## 🚀 Quick Start

Get started in 5 minutes! Follow our **[Quick Start Guide](docs/getting-started/quickstart.md)** for detailed instructions.

### TL;DR

```powershell
# 1. Start services
cd slack-cline
docker-compose up

# 2. Start dashboard (new terminal)
cd frontend
npm install
npm run dev

# 3. Configure at http://localhost:3001/settings
# 4. Create project at http://localhost:3001/projects
# 5. Test at http://localhost:3001/admin
```

**Dashboard:** http://localhost:3001  
**Backend API:** http://localhost:8000

📚 **Full Guide:** [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md)

## 💬 Usage

### Primary Interaction: @mentions

Just @mention Sline anywhere in Slack:

```
@sline what files are in the src directory?
@sline can you explain how the auth module works?
@sline search for TODO comments in the codebase
```

Sline will:
- Automatically use tools to answer your question
- Respond in a thread (keeps channel clean)
- Remember the conversation if you follow up

### Secondary: Slash Commands (Utilities)

```
/cline help     # Show how to interact with Sline
/cline status   # Show active conversations
```

### Multi-Turn Conversations

```
You: @sline what's in the README?
Sline: Looking at README.md, it's a FastAPI backend service...

You: @sline can you find the main entry point?
Sline: Sure! Looking at the codebase... The main entry point is `main.py`...

You: @sline what does it import?
Sline: [Checks code] It imports FastAPI, uvicorn, and the routers...
```

Each thread maintains full conversation history!

## 🛠️ Development

Full development guide: **[docs/development/setup.md](docs/development/setup.md)**

### Key Technologies

- **LangGraph** - Agent workflow orchestration
- **LangChain** - Tool integration and LLM abstraction
- **FastAPI** - Async Python web framework
- **PostgreSQL** - Conversation and project storage
- **React + Vite** - Dashboard interface
- **Docker** - Containerization

### Debugging

Use VS Code debugger with Docker:
```powershell
# Enable debug mode in docker-compose.yml
docker-compose up
# Press F5 in VS Code to attach
```

📚 **Full Guide:** [docs/development/debugging.md](docs/development/debugging.md)

## 📊 Dashboard Features

The dashboard is your **testing and configuration interface**:

- **📁 Projects** - Configure repositories
- **⚙️ Settings** - Set up LLM API keys  
- **🧪 Admin Panel** - Test without Slack
- **📈 Home** - Overview statistics

📚 **Full Guide:** [docs/user-guide/dashboard.md](docs/user-guide/dashboard.md)

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `CLINE_PROVIDER` | LLM provider | Yes | `anthropic` |
| `CLINE_API_KEY` | LLM API key | Yes | - |
| `CLINE_MODEL_ID` | Model identifier | Yes | - |
| `SLACK_BOT_TOKEN` | Slack bot token | Yes | - |
| `SLACK_SIGNING_SECRET` | Slack signing secret | Yes | - |
| `SLACK_BOT_USER_ID` | Bot's user ID (for @mentions) | Yes | - |
| `DATABASE_URL` | PostgreSQL connection | No | Auto-configured |
| `LOG_LEVEL` | Logging verbosity | No | `INFO` |

### Slack App Setup

**Required Permissions** (Bot Token Scopes):
- `chat:write` - Post messages to channels
- `app_mentions:read` - Receive @mention events
- `channels:history` - Read channel messages  (for thread context)
- `im:history` - Read DM messages (for DM support)

**Event Subscriptions**:
- Subscribe to: `app_mention`, `message.channels`, `message.im`
- Request URL: `https://your-domain.com/slack/events`

**Slash Commands** (Optional):
- Command: `/cline`
- Request URL: `https://your-domain.com/slack/events`

## 🧪 Testing

### Dashboard Testing (No Slack Required)

1. Start services: `docker-compose up`
2. Start dashboard: `cd frontend && npm run dev`
3. Configure API keys: http://localhost:3001/settings
4. Create project: http://localhost:3001/projects
5. Test agent: http://localhost:3001/admin

This tests the complete agent flow without Slack setup!

### Manual Testing

```bash
# Check backend health
curl http://localhost:8000/health

# View database
docker-compose exec db psql -U postgres -d slack_cline
  SELECT * FROM conversations;

# View logs
docker-compose logs -f backend

# Check workspace directory
ls -la slack-cline/data/workspaces/
```

## 📝 Documentation

### 📚 Complete Documentation

All documentation is now in the **[docs/](docs/)** folder:

- **[Getting Started](docs/getting-started/quickstart.md)** - 5-minute setup guide
- **[User Guide](docs/user-guide/dashboard.md)** - Using Sline and dashboard
- **[Architecture](docs/architecture/overview.md)** - System design deep dive
- **[Development](docs/development/setup.md)** - Dev environment setup
- **[Debugging](docs/development/debugging.md)** - VS Code debugging guide

### 🔗 Quick Links

- [Quick Start](docs/getting-started/quickstart.md) - Get running in 5 minutes
- [Dashboard Guide](docs/user-guide/dashboard.md) - Testing interface
- [Architecture Overview](docs/architecture/overview.md) - How it works
- [Multi-Project Setup](docs/architecture/multi-project.md) - LLM classification
- [API Reference](docs/development/api-reference.md) - REST endpoints *(coming soon)*

## 🚢 Deployment

See **[docs/getting-started/quickstart.md](docs/getting-started/quickstart.md)** for production deployment checklist.

**Key Steps:**
1. Deploy Docker container to cloud platform
2. Configure Slack Event Subscriptions
3. Set up managed PostgreSQL
4. Configure SSL/HTTPS
5. Secure API keys

## 🆘 Troubleshooting

Common issues and solutions: **[docs/user-guide/troubleshooting.md](docs/user-guide/troubleshooting.md)** *(coming soon)*

**Quick Checks:**
```powershell
# Backend health
curl http://localhost:8000/health

# View logs
docker-compose logs -f backend

# Check database
docker-compose exec db psql -U postgres -d slack_cline
```

For detailed troubleshooting, see the [Quick Start Guide](docs/getting-started/quickstart.md#troubleshooting).


## 🤝 Contributing

This is an active development project. Key areas for contribution:

- **Phase 2**: Planning and execution nodes
- **Phase 3**: Advanced tools (execute_command, code analysis)
- **Phase 4**: Repository cloning and workspace management
- **Testing**: Unit tests for agent nodes and tools

## 📄 License

MIT License - see LICENSE file for details.

## 🚀 What's Next?

**Current State (MVP)**:
- ✅ @mention-based conversational interaction
- ✅ Thread-aware multi-turn conversations
- ✅ Autonomous tool usage (read, search, list)
- ✅ LLM-based multi-project classification
- ✅ Persistent conversation state

**Coming Soon (Phase 2)**:
- 📋 Implementation planning workflow
- ✅ Approval buttons in Slack
- ✏️ Write tools (file editing)
- 🚀 Plan execution

**Future (Phase 3+)**:
- 🌳 Code analysis with tree-sitter
- 💻 Command execution with output streaming
- 🔀 Git operations (commit, branch, PR)
- 📊 Team analytics dashboard

---

**Ready to get started?** → **[Quick Start Guide](docs/getting-started/quickstart.md)** 🎉
