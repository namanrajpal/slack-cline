# Slack-Cline Integration

A FastAPI-based backend service that integrates Slack with Cline Core via gRPC, enabling developers to trigger Cline runs directly from Slack channels and see progress updates in real-time.

## 🏗️ Architecture

The system follows a clean three-tier architecture:

- **Slack Gateway**: HTTP endpoints for Slack webhooks with signature verification
- **Run Orchestrator**: Business logic coordinating between Slack, database, and Cline Core  
- **Execution Engine**: gRPC client wrapper for communicating with Cline Core

```
Slack Workspace ←→ FastAPI Backend ←→ Cline Core (gRPC)
                        ↓
                   PostgreSQL
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for Cline Core)
- Python 3.12+ (for local development)
- A Slack workspace where you can install apps

### 1. Set Up Cline Core (One-Time Setup)

Cline Core is the gRPC server that runs the actual AI agent:

```bash
cd cline

# Install dependencies and compile Cline Core
npm install
npm run compile-standalone

# This creates dist-standalone/cline-core.js
```

### 2. Compile Proto Files (One-Time Setup)

```bash
cd ../slack-cline

# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Compile Cline proto files to Python gRPC code
cd backend
python compile_protos.py
cd ..
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Slack credentials
```

Edit `.env`:
```bash
SLACK_SIGNING_SECRET=your_slack_signing_secret_here
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
CLINE_CORE_HOST=localhost
CLINE_CORE_PORT=50051
```

### 4. Start All Services

```bash
# Terminal 1: Start Cline Core
cd cline
node dist-standalone/cline-core.js --port 50051

# Terminal 2: Start PostgreSQL and Backend
cd slack-cline
docker-compose up

# Terminal 3: Expose to internet (for Slack webhooks)
ngrok http 8000
```

The backend will be available at `http://localhost:8000`.

📚 **For detailed setup instructions, see [GETTING_STARTED.md](./GETTING_STARTED.md)**

### 4. Configure Slack App

Create a new Slack app at [api.slack.com](https://api.slack.com/apps):

**Slash Commands:**
- Command: `/cline`
- Request URL: `https://your-domain.com/slack/events`
- Description: "Trigger Cline runs from Slack"

**Interactivity & Shortcuts:**
- Request URL: `https://your-domain.com/slack/interactivity`

**OAuth & Permissions:**
Required bot token scopes:
- `chat:write` - Post messages
- `commands` - Receive slash commands

**Event Subscriptions:** (Optional)
- Request URL: `https://your-domain.com/slack/events`


## 💬 Usage

### Basic Commands

```bash
# Start a new Cline run
/cline run fix failing unit tests

# Check run status  
/cline status

# Get help
/cline help
```

### Interactive Features

- **Progress Updates**: Real-time progress shown in Slack threads
- **Cancel Button**: Click to cancel running tasks
- **Status Indicators**: Emoji-based status (⏳ 🔧 ✅ ❌ ⏹️)

### Channel Setup

For MVP, the system creates a default repository mapping for each channel. In production, you'd configure channel → repository mappings through an admin interface.

## 🛠️ Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL (or use Docker)
docker-compose up db -d

# Run the application
cd backend
python main.py
```

### Project Structure

```
slack-cline/
├── backend/                    # FastAPI application
│   ├── main.py                # Application entry point
│   ├── config.py              # Configuration management
│   ├── database.py            # Database setup
│   ├── models/                # SQLAlchemy models
│   │   ├── project.py         # Channel→repo mapping
│   │   └── run.py             # Run tracking
│   ├── schemas/               # Pydantic schemas
│   │   ├── slack.py           # Slack webhook validation
│   │   └── run.py             # Run API schemas
│   ├── modules/               # Core business logic
│   │   ├── slack_gateway/     # Slack webhook handling
│   │   ├── orchestrator/      # Run lifecycle management
│   │   └── execution_engine/  # Cline Core gRPC client
│   ├── utils/                 # Utilities
│   │   ├── logging.py         # Structured logging
│   │   └── slack_client.py    # Slack API wrapper
│   └── proto/                 # gRPC proto definitions
├── docker-compose.yml         # Local development environment
├── Dockerfile                 # Backend container
└── requirements.txt           # Python dependencies
```

### Key Components

**Slack Gateway** (`modules/slack_gateway/`)
- Handles webhook signature verification
- Parses slash commands and interactive components
- Converts Slack events to internal commands

**Run Orchestrator** (`modules/orchestrator/`)
- Manages complete run lifecycle
- Coordinates between Slack, database, and Cline Core
- Handles event streaming and status updates

**Execution Engine** (`modules/execution_engine/`)
- gRPC client for Cline Core communication
- Translates between domain models and proto messages
- Manages connections and streaming

### Database Models

**Projects Table:**
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    slack_channel_id VARCHAR(255) NOT NULL,
    repo_url VARCHAR(512) NOT NULL,
    default_ref VARCHAR(255) DEFAULT 'main',
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**Runs Table:**
```sql
CREATE TABLE runs (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    project_id UUID REFERENCES projects(id),
    cline_run_id VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    task_prompt TEXT NOT NULL,
    slack_channel_id VARCHAR(255),
    slack_thread_ts VARCHAR(255),
    created_at TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    summary TEXT
);
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `PORT` | Server port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `SLACK_SIGNING_SECRET` | Slack app signing secret | Required |
| `SLACK_BOT_TOKEN` | Slack bot token | Required |
| `CLINE_CORE_HOST` | Cline Core gRPC host | `localhost` |
| `CLINE_CORE_PORT` | Cline Core gRPC port | `50051` |
| `CLINE_CORE_TIMEOUT` | gRPC timeout (seconds) | `300` |

### Slack App Configuration

Your Slack app needs these configurations:

1. **Slash Commands**: `/cline` pointing to `/slack/events`
2. **Interactivity**: Button clicks pointing to `/slack/interactivity`  
3. **Bot Token Scopes**: `chat:write`, `commands`
4. **Signing Secret**: For webhook verification

## 📝 API Endpoints

### Health Checks
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health with dependencies
- `GET /slack/health` - Slack Gateway health

### Slack Integration
- `POST /slack/events` - Slash command webhooks
- `POST /slack/interactivity` - Interactive component webhooks

## 🔍 Monitoring & Logging

The application uses structured logging with JSON output in production:

```bash
# View logs
docker-compose logs -f backend

# Filter by component
docker-compose logs -f backend | grep "slack.gateway"
docker-compose logs -f backend | grep "orchestrator" 
docker-compose logs -f backend | grep "execution.client"
```

Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## 🚢 Deployment

### Production Setup

1. **Environment**: Set production environment variables
2. **Database**: Use managed PostgreSQL (RDS, Cloud SQL)
3. **SSL**: Enable HTTPS with valid certificates
4. **Monitoring**: Add application monitoring (Sentry, DataDog)
5. **Scaling**: Use container orchestration (K8s, ECS)

### Docker Production Build

```bash
# Build production image
docker build -t slack-cline-backend .

# Run with production config
docker run -d \
  --name slack-cline-backend \
  -p 8000:8000 \
  --env-file .env.production \
  slack-cline-backend
```

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock

# Run tests
pytest tests/

# Run with coverage
pytest --cov=backend tests/
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

**"Slack signature verification failed"**
- Check that `SLACK_SIGNING_SECRET` matches your Slack app
- Ensure your webhook URL is accessible from the internet
- Verify the request is reaching the correct endpoint

**"No repository configured for channel"**
- The system auto-creates default repository mappings for MVP
- Check logs for project creation messages
- Verify database connectivity

**"Failed to connect to Cline Core"**
- Ensure Cline Core is running and accessible
- Check `CLINE_CORE_HOST` and `CLINE_CORE_PORT` settings
- Verify gRPC connectivity

**Database connection issues**
- Verify PostgreSQL is running
- Check `DATABASE_URL` format: `postgresql+asyncpg://user:pass@host:port/db`
- Ensure database exists and user has proper permissions

### Getting Help

1. Check application logs: `docker-compose logs -f backend`
2. Verify configuration in `.env`
3. Test connectivity to external services (Slack, Cline Core, database)
4. Check Slack app configuration matches documentation

## 🔗 Related Projects

- [Cline](https://github.com/cline/cline) - AI coding agent
- [Slack Bolt](https://slack.dev/bolt-js/) - Slack app framework
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
