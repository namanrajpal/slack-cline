# Sline Documentation

Welcome to Sline - your AI coding teammate that lives in Slack! 👋

## 📚 Documentation Structure

### 🚀 Getting Started
- **[Quick Start](getting-started/quickstart.md)** - Get up and running in 5 minutes
- **[Installation Guide](getting-started/installation.md)** - Detailed setup instructions
- **[Your First Conversation](getting-started/first-conversation.md)** - Tutorial for using Sline

### 📖 User Guide
- **[Using Sline in Slack](user-guide/slack-usage.md)** - @mention commands and conversations
- **[Dashboard Guide](user-guide/dashboard.md)** - Testing and configuration interface
- **[Project Management](user-guide/projects.md)** - Setting up repositories
- **[Troubleshooting](user-guide/troubleshooting.md)** - Common issues and solutions

### 🏗️ Architecture
- **[Architecture Overview](architecture/overview.md)** - System design and components
- **[Agent System](architecture/agent-system.md)** - SlineBrain and LangGraph details
- **[Conversation Model](architecture/conversation-model.md)** - State persistence and threads
- **[Multi-Project Classification](architecture/multi-project.md)** - LLM-based project selection

### 🛠️ Development
- **[Development Setup](development/setup.md)** - Local development environment
- **[Debugging Guide](development/debugging.md)** - Using VS Code debugger with Docker
- **[API Reference](development/api-reference.md)** - REST API documentation

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
- [How to Use Sline](user-guide/slack-usage.md)
- [Common Issues](user-guide/troubleshooting.md)

### For Developers
- [Development Setup](development/setup.md)
- [Architecture Deep Dive](architecture/overview.md)
- [Contributing Guidelines](development/contributing.md)

### For Administrators
- [Production Deployment](../README.md#deployment)
- [Slack App Configuration](user-guide/slack-usage.md#slack-app-setup)
- [Environment Variables](development/setup.md#configuration)

## 📞 Support & Community

- **Issues**: [GitHub Issues](https://github.com/your-org/sline/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/sline/discussions)
- **Email**: support@sline.example.com

## 📄 License

MIT License - see [LICENSE](../LICENSE) for details.

---

**Ready to get started?** → [Quick Start Guide](getting-started/quickstart.md)
