# Sline Documentation

Welcome to Sline - your AI coding teammate that lives in Slack! 👋

## 📚 Documentation Structure

### 🚀 Getting Started
- **[Quick Start](getting-started/quickstart.md)** - Get up and running in 5 minutes
- **[Installation Guide](getting-started/installation.md)** - Detailed setup instructions
- **[Your First Conversation](getting-started/first-conversation.md)** - Tutorial for using Sline

### 📖 User Guide
- **[Dashboard Guide](user-guide/dashboard.md)** - Central hub for managing your agent
- **[Integrations Guide](user-guide/integrations.md)** - MCP servers, rules, and API integrations
- **[Conversations Guide](user-guide/conversations.md)** - Understanding the conversation model
<!-- Coming Soon:
- **[Using Sline in Slack](user-guide/slack-usage.md)** - @mention commands and conversations
- **[Project Management](user-guide/projects.md)** - Setting up repositories
- **[Troubleshooting](user-guide/troubleshooting.md)** - Common issues and solutions
-->

### 🏗️ Architecture
- **[Architecture Overview](architecture/overview.md)** - System design and components
- **[Multi-Project Classification](architecture/multi-project.md)** - LLM-based project selection
<!-- Coming Soon:
- **[Agent System](architecture/agent-system.md)** - SlineBrain and LangGraph details
- **[Conversation Model](architecture/conversation-model.md)** - State persistence and threads
-->

### 🛠️ Development
- **[Debugging Guide](development/debugging.md)** - Using VS Code debugger with Docker
- **[Slack Formatting](development/slack-formatting.md)** - Formatting messages for Slack
<!-- Coming Soon:
- **[Development Setup](development/setup.md)** - Local development environment
- **[API Reference](development/api-reference.md)** - REST API documentation
- **[Frontend Structure](development/frontend-structure.md)** - React component architecture
-->

## 🎯 What is Sline?

Sline is a **conversational AI coding assistant** that integrates seamlessly into your Slack workspace. Instead of command-line tools or separate interfaces, Sline becomes part of your team's natural conversation flow.

### Key Features
- 💬 **Conversational** - Just @mention Sline in any Slack message
- 🧵 **Thread-aware** - Maintains context across multi-turn discussions
- 🔧 **Autonomous** - Uses tools (read files, search code) automatically
- 💾 **Persistent** - Conversations survive server restarts
- 🎯 **Multi-project** - Intelligently selects the right codebase

## 🤖 How It Works

```
#your-channel

👤 You: @sline what files are in this project?

🤖 Sline: Hey! 👋 Looking at the codebase...
         [automatically uses list_files tool]
         
         I found:
         • README.md
         • src/ (main source code)
         • tests/ (test suite)
         
         Want me to explore any specific directory?

👤 You: @sline can you check the tests?

🤖 Sline: Sure! Looking at the tests directory...
         [conversation continues naturally]
```

## 🚀 Quick Links

### For Users
- [Get Started in 5 Minutes](getting-started/quickstart.md)
- [Dashboard Guide](user-guide/dashboard.md)
- [Integrations Guide](user-guide/integrations.md)
- [Conversations Guide](user-guide/conversations.md)

### For Developers
- [Development Setup](development/setup.md)
- [Architecture Deep Dive](architecture/overview.md)
- [Contributing Guidelines](development/contributing.md)

### For Administrators
- [Production Deployment](../README.md#deployment)
- [Environment Variables](getting-started/quickstart.md#configuration-files)
<!-- Coming Soon:
- [Slack App Configuration](user-guide/slack-usage.md#slack-app-setup)
-->

## 📞 Support & Community

- **Issues**: [GitHub Issues](https://github.com/namanrajpal/slack-cline/issues)
- **Discussions**: [GitHub Discussions](https://github.com/namanrajpal/slack-cline/discussions)

## 📄 License

MIT License - see [LICENSE](../LICENSE) for details.

---

**Ready to get started?** → [Quick Start Guide](getting-started/quickstart.md)
