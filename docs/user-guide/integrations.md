# Integrations Guide

Extend Sline's capabilities with MCP servers, custom rules, and API integrations.

---

## 🧩 What are Integrations?

Integrations allow you to extend Sline beyond its core capabilities by connecting to:

- **MCP Servers** - Model Context Protocol servers for additional tools
- **Rules** - Project-specific configuration and guidelines
- **External APIs** - Third-party services (coming soon)

---

## 🖥️ MCP Servers

**Model Context Protocol (MCP)** servers provide additional tools and data sources for your AI agent.

### What is MCP?

MCP is a standard protocol for exposing tools and resources to AI agents. Think of it as a plugin system that lets you extend what Sline can do.

### Server Types

#### 🗂️ Filesystem Server
Access files and directories on your system.

**Use Cases:**
- Read configuration files
- Access documentation directories
- Browse workspace files outside project root

**Example Configuration:**
```json
{
  "name": "Documentation Folder",
  "type": "filesystem",
  "endpoint": "/path/to/docs",
  "auth_method": "none"
}
```

#### 🌿 Git Server
Interact with Git repositories.

**Use Cases:**
- Commit changes
- Create branches
- View git history
- Merge branches

**Example Configuration:**
```json
{
  "name": "Git Operations",
  "type": "git",
  "endpoint": "https://github.com/user/repo.git",
  "auth_method": "api_key",
  "auth_config": {
    "api_key": "ghp_your_token_here"
  }
}
```

#### 🌐 HTTP Server
Make API calls to external services.

**Use Cases:**
- Call REST APIs
- Fetch external data
- Trigger webhooks
- Query microservices

**Example Configuration:**
```json
{
  "name": "Internal API",
  "type": "http",
  "endpoint": "https://api.internal.com",
  "auth_method": "api_key",
  "auth_config": {
    "api_key": "your_api_key",
    "header_name": "X-API-Key"
  }
}
```

#### 🗄️ Database Server
Query and modify database records.

**Use Cases:**
- Run SQL queries
- Check database schema
- View table data
- Execute migrations

**Example Configuration:**
```json
{
  "name": "Production DB (Read-only)",
  "type": "database",
  "endpoint": "postgresql://host:5432/dbname",
  "auth_method": "basic",
  "auth_config": {
    "username": "readonly_user",
    "password": "secure_password"
  }
}
```

#### 🔧 Custom Server
Build your own MCP server integration.

**Use Cases:**
- Custom business logic
- Proprietary systems
- Internal tools
- Specialized workflows

---

## 🚀 Adding an MCP Server

### Step-by-Step Guide

1. **Navigate to Integrations**
   - Open dashboard at http://localhost:3001
   - Click "Integrations" in sidebar
   - Go to "MCP Servers" tab

2. **Click "Add MCP Server"**
   - Dialog opens with configuration form

3. **Configure Server**
   - **Server Name**: Descriptive name (e.g., "Project Workspace")
   - **Server Type**: Choose from filesystem/git/http/database/custom
   - **Endpoint/URL**: Connection string or path
   - **Authentication**: Select method (none/api_key/oauth/basic)

4. **Enter Authentication Details** (if required)
   - **API Key**: For api_key method
   - **Username/Password**: For basic auth
   - **OAuth Config**: For OAuth method

5. **Save and Test**
   - Click "Add Server"
   - Test connection (coming soon)

### Example: Setting Up Filesystem Access

Let's add a filesystem server to access documentation:

```yaml
Server Name: Documentation Directory
Type: Filesystem
Endpoint: /home/user/projects/docs
Authentication: None
```

This allows Sline to read files from your docs directory.

---

## ⚙️ MCP Server Configuration

### Authentication Methods

#### None
No authentication required (local filesystem, public APIs).

```json
{
  "auth_method": "none"
}
```

#### API Key
Bearer token or API key authentication.

```json
{
  "auth_method": "api_key",
  "auth_config": {
    "api_key": "your_key_here"
  }
}
```

#### OAuth
OAuth 2.0 flow (coming soon).

```json
{
  "auth_method": "oauth",
  "auth_config": {
    "client_id": "your_client_id",
    "client_secret": "your_secret",
    "redirect_uri": "http://localhost:3001/oauth/callback"
  }
}
```

#### Basic Auth
Username and password.

```json
{
  "auth_method": "basic",
  "auth_config": {
    "username": "user",
    "password": "pass"
  }
}
```

---

## 📋 Rules (Coming Soon)

**Per-project `.clinerules`** for customizing agent behavior per codebase.

### What are Rules?

Rules are project-specific instructions that tell Sline how to work with different codebases:

- **Code Style**: Formatting preferences, linting rules
- **Testing**: Required tests, coverage thresholds
- **Deployment**: CI/CD workflows, staging requirements
- **Team Conventions**: Naming patterns, file structure

### Rules Structure

```
project-root/
└── .clinerules/
    ├── code-style.md       # Formatting and linting rules
    ├── testing.md          # Test requirements
    ├── deployment.md       # Deploy workflows
    └── conventions.md      # Team conventions
```

### Example Rule File

**`.clinerules/code-style.md`:**
```markdown
# Code Style Rules

## Python
- Use Black formatter with line length 88
- Follow PEP 8 conventions
- Type hints required for all functions

## TypeScript
- Use Prettier with 2-space indentation
- Strict mode enabled
- No `any` types allowed

## Git Commits
- Use conventional commits (feat:, fix:, docs:)
- Reference issue numbers in commit messages
```

### How Rules Work

1. **Project Detection**: Sline identifies which project you're working on
2. **Load Rules**: Reads `.clinerules/` from project root
3. **Apply Context**: Includes rules in agent context
4. **Follow Guidelines**: Agent respects rules when making changes

### Benefits

- ✅ Consistent code across team
- ✅ Automated enforcement
- ✅ Project-specific customization
- ✅ Easy onboarding for new team members

---

## 🔗 API Integrations (Coming Soon)

Connect external services to expand Sline's capabilities.

### Planned Integrations

#### Issue Tracking
- **Jira** - Create tickets, update status, add comments
- **Linear** - Create issues, assign to team members
- **GitHub Issues** - Manage issues and PRs

#### CI/CD Systems
- **GitHub Actions** - Trigger workflows, check status
- **GitLab CI** - Monitor pipelines, restart jobs
- **CircleCI** - View build logs, retry failed builds

#### Monitoring & Observability
- **Datadog** - Query metrics, check alerts
- **Sentry** - View error reports, triage issues
- **New Relic** - Monitor performance, analyze traces

#### Communication
- **Slack** (native) - Already integrated!
- **Microsoft Teams** - Send notifications
- **Discord** - Post to channels

### Integration Workflow

```
User: "@sline create a Jira ticket for the auth bug"
  ↓
Sline identifies Jira integration
  ↓
Calls Jira API to create ticket
  ↓
Returns ticket URL and confirmation
```

---

## 🔒 Security Best Practices

### API Keys

**DO:**
- ✅ Store keys in environment variables
- ✅ Use read-only keys when possible
- ✅ Rotate keys regularly
- ✅ Limit key scopes/permissions

**DON'T:**
- ❌ Commit keys to version control
- ❌ Share keys in chat or email
- ❌ Use personal keys for team projects
- ❌ Give keys more permissions than needed

### Database Access

**Recommendations:**
- Use read-only database users for queries
- Never give write access to production databases
- Use database firewalls to restrict access
- Monitor query logs for suspicious activity

### Filesystem Access

**Best Practices:**
- Limit filesystem servers to specific directories
- Don't expose sensitive paths (e.g., `/etc`, `/root`)
- Use read-only mounts when possible
- Audit file access regularly

---

## 🐛 Troubleshooting

### MCP Server Not Working

**Problem:** Server added but not accessible to agent

**Solutions:**
1. Check backend logs for errors
2. Verify endpoint URL is correct
3. Test authentication credentials
4. Ensure server is running (for custom servers)
5. Check network connectivity

### Authentication Fails

**Problem:** "Authentication failed" error

**Solutions:**
1. Verify API key is valid and not expired
2. Check key has required permissions
3. Ensure correct authentication method selected
4. Try regenerating the API key
5. Check for typos in credentials

### Permission Denied

**Problem:** Agent can't access resources

**Solutions:**
1. Check file/directory permissions
2. Verify user has access to endpoint
3. Ensure API key has required scopes
4. Check firewall/network rules
5. Review server logs for details

---

## 💡 Integration Ideas

### Development Workflows

**Code Review Assistant:**
```
MCP Servers:
- GitHub API (read PRs, post comments)
- Code Analysis Tool (lint, security scan)

Workflow:
User: "@sline review PR #123"
→ Fetch PR diff
→ Run linters
→ Post review comments
```

**Database Inspector:**
```
MCP Servers:
- PostgreSQL (read-only)
- Monitoring API (query metrics)

Workflow:
User: "@sline check slow queries"
→ Query database stats
→ Analyze performance
→ Suggest indexes
```

**Documentation Generator:**
```
MCP Servers:
- Filesystem (read source code)
- GitHub API (create PR with docs)

Workflow:
User: "@sline document the API module"
→ Read source files
→ Generate markdown docs
→ Create PR with changes
```

---

## 🚀 Next Steps

- **[Dashboard Guide](dashboard.md)** - Learn to configure integrations via dashboard
- **[Conversations Guide](conversations.md)** - Understand how agent uses tools
- **[Architecture Overview](../architecture/overview.md)** - Deep dive into MCP integration

---

## 📚 Resources

- **[MCP Specification](https://modelcontextprotocol.io)** - Official protocol docs
- **[MCP Server Examples](https://github.com/modelcontextprotocol)** - Sample implementations
- **[Building Custom Servers](../development/mcp-servers.md)** - Developer guide (coming soon)

---

**Questions?** Open an issue on [GitHub](https://github.com/your-org/sline/issues) or check the troubleshooting guide.
