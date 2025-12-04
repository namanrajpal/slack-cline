# Implementation Plan

[Overview]
Create a FastAPI-based backend service that integrates Slack with Cline Core via gRPC to enable developers to trigger Cline runs directly from Slack channels and see progress updates in real-time.

The implementation follows the architecture outlined in ARCHITECTURE.md with three core modules: Slack Gateway (HTTP endpoints for Slack webhooks), Run Orchestrator (business logic and state management), and Execution Engine (gRPC client wrapper for Cline Core). The system maps Slack channels to Git repositories, manages run lifecycle in PostgreSQL, and streams progress updates back to Slack threads. This creates a seamless developer experience where `/cline run <task>` commands in Slack trigger automated code changes with full visibility and control.

[Types]
Define core domain models and data structures for the slack-cline integration system.

**Database Models:**
- `Project`: Maps Slack channels to Git repositories with fields: id (UUID), tenant_id (str), slack_channel_id (str), repo_url (str), default_ref (str), created_at (datetime), updated_at (datetime)
- `Run`: Tracks execution lifecycle with fields: id (UUID), tenant_id (str), project_id (UUID FK), cline_run_id (str), status (enum: QUEUED/RUNNING/SUCCEEDED/FAILED/CANCELLED), task_prompt (str), slack_channel_id (str), slack_thread_ts (str), created_at (datetime), started_at (datetime), finished_at (datetime), summary (str)

**API Models (Pydantic):**
- `SlackCommand`: Validates slash command payload with channel_id, user_id, text fields
- `StartRunCommand`: Internal command with tenant_id, channel_id, user_id, task_prompt
- `RunEvent`: Domain event with run_id, event_type, timestamp, data fields
- `ProjectConfig`: Configuration for channel-to-repo mapping

**gRPC Integration Models:**
- `ClineRunRequest`: Maps to Cline Core's StartRunRequest proto
- `ClineEvent`: Maps from Cline Core's RunEvent proto messages

[Files]
Detailed breakdown of all files to be created and their purposes.

**New files to be created:**
- `slack-cline/backend/main.py` - FastAPI application entry point with CORS, health endpoints
- `slack-cline/backend/config.py` - Configuration management using Pydantic Settings
- `slack-cline/backend/database.py` - SQLAlchemy setup, connection management, and session handling
- `slack-cline/backend/models/` - SQLAlchemy ORM models directory
- `slack-cline/backend/models/project.py` - Project database model
- `slack-cline/backend/models/run.py` - Run database model with status enum
- `slack-cline/backend/schemas/` - Pydantic schemas for API validation
- `slack-cline/backend/schemas/slack.py` - Slack webhook payload schemas
- `slack-cline/backend/schemas/run.py` - Run-related API schemas
- `slack-cline/backend/modules/` - Core business logic modules
- `slack-cline/backend/modules/slack_gateway/` - Slack integration module
- `slack-cline/backend/modules/slack_gateway/handlers.py` - HTTP endpoint handlers
- `slack-cline/backend/modules/slack_gateway/verification.py` - Slack signature verification
- `slack-cline/backend/modules/orchestrator/` - Run orchestration module
- `slack-cline/backend/modules/orchestrator/service.py` - Main orchestrator business logic
- `slack-cline/backend/modules/orchestrator/events.py` - Event handling and streaming
- `slack-cline/backend/modules/execution_engine/` - gRPC client wrapper
- `slack-cline/backend/modules/execution_engine/client.py` - Cline Core gRPC client
- `slack-cline/backend/modules/execution_engine/translator.py` - Proto message translation
- `slack-cline/backend/utils/` - Utility modules
- `slack-cline/backend/utils/logging.py` - Structured logging setup
- `slack-cline/backend/utils/slack_client.py` - Slack Web API client wrapper
- `slack-cline/backend/proto/` - Generated gRPC code (copied from Cline)
- `slack-cline/requirements.txt` - Python dependencies
- `slack-cline/docker-compose.yml` - Local development environment
- `slack-cline/Dockerfile` - Backend service containerization
- `slack-cline/.env.example` - Environment variable template
- `slack-cline/README.md` - Getting started guide and documentation

**Configuration files:**
- `.dockerignore` - Docker build exclusions
- `.gitignore` - Python and IDE ignores

[Functions]
Detailed breakdown of key functions to implement across modules.

**Slack Gateway Functions:**
- `slack_gateway.handlers.handle_slash_command(payload: SlackCommand) -> JSONResponse` - Parse and validate `/cline run` commands
- `slack_gateway.handlers.handle_interactivity(payload: dict) -> JSONResponse` - Handle button clicks and cancellations
- `slack_gateway.verification.verify_slack_signature(timestamp: str, body: bytes, signature: str) -> bool` - Verify webhook authenticity

**Run Orchestrator Functions:**
- `orchestrator.service.create_run(command: StartRunCommand) -> UUID` - Initialize new run in database
- `orchestrator.service.resolve_project(tenant_id: str, channel_id: str) -> Project` - Map channel to repository
- `orchestrator.service.start_execution(run: Run) -> str` - Call execution engine and update run status
- `orchestrator.events.handle_run_event(event: RunEvent) -> None` - Process Cline progress events
- `orchestrator.events.update_slack_thread(run: Run, event: RunEvent) -> None` - Send progress to Slack

**Execution Engine Functions:**
- `execution_engine.client.start_run(repo_url: str, ref: str, prompt: str) -> str` - Start Cline gRPC run
- `execution_engine.client.stream_events(cline_run_id: str) -> AsyncIterator[RunEvent]` - Subscribe to Cline events
- `execution_engine.client.cancel_run(cline_run_id: str) -> None` - Cancel running Cline task
- `execution_engine.translator.grpc_to_domain_event(grpc_event: Any) -> RunEvent` - Convert proto messages

**Database Functions:**
- `database.get_session() -> AsyncSession` - Database session dependency
- `database.create_tables() -> None` - Initialize database schema

**Utility Functions:**
- `utils.slack_client.post_message(channel: str, text: str, thread_ts: str) -> dict` - Send Slack messages
- `utils.logging.setup_logging(level: str) -> None` - Configure structured logging

[Classes]
Detailed breakdown of key classes and their responsibilities.

**New classes:**
- `SlackGatewayService` in `modules/slack_gateway/handlers.py` - Handles HTTP endpoints, validates webhooks, converts Slack payloads to internal commands
- `RunOrchestratorService` in `modules/orchestrator/service.py` - Manages run lifecycle, coordinates between gateway and execution engine, handles database operations
- `ExecutionEngineClient` in `modules/execution_engine/client.py` - Wraps gRPC communication with Cline Core, manages connection pooling and retries
- `EventStreamHandler` in `modules/orchestrator/events.py` - Processes Cline events, updates database, sends Slack notifications
- `SlackClient` in `utils/slack_client.py` - Wrapper for Slack Web API operations
- `ConfigSettings` in `config.py` - Pydantic settings class for configuration management

**Database model classes:**
- `ProjectModel` in `models/project.py` - SQLAlchemy model for channel-to-repo mapping
- `RunModel` in `models/run.py` - SQLAlchemy model for run tracking with relationships

**Schema classes:**
- `SlackCommandSchema` in `schemas/slack.py` - Pydantic validation for slash commands
- `RunResponseSchema` in `schemas/run.py` - API response schemas for run data

[Dependencies]
Specification of external packages and version requirements.

**Core FastAPI Dependencies:**
- `fastapi==0.104.1` - Modern async web framework
- `uvicorn[standard]==0.24.0` - ASGI server with performance optimizations
- `pydantic==2.5.0` - Data validation and settings management
- `pydantic-settings==2.1.0` - Environment-based configuration

**Database Dependencies:**
- `sqlalchemy[asyncio]==2.0.23` - Async ORM with PostgreSQL support
- `asyncpg==0.29.0` - High-performance PostgreSQL driver
- `alembic==1.12.1` - Database migration tool (for future use)

**gRPC Dependencies:**
- `grpcio==1.60.0` - Python gRPC runtime
- `grpcio-tools==1.60.0` - Protocol buffer compiler tools
- `protobuf==4.25.1` - Protocol buffer runtime

**Slack Integration:**
- `slack-sdk==3.24.0` - Official Slack Web API client
- `httpx==0.25.2` - Async HTTP client for webhook calls

**Development and Monitoring:**
- `structlog==23.2.0` - Structured logging for observability
- `python-multipart==0.0.6` - Form data parsing for webhooks

[Testing]
Testing strategy and test file organization.

**Unit Testing Approach:**
- Use `pytest==7.4.3` with `pytest-asyncio==0.21.1` for async test support
- Mock external dependencies (gRPC, Slack API, database) using `pytest-mock==3.12.0`
- Test files mirror source structure with `test_` prefix

**Test Files Required:**
- `tests/test_slack_gateway.py` - Test webhook handling, signature verification, payload parsing
- `tests/test_orchestrator.py` - Test run lifecycle, event handling, database operations
- `tests/test_execution_engine.py` - Test gRPC client, message translation, error handling
- `tests/test_database.py` - Test model relationships, queries, and migrations
- `conftest.py` - Shared fixtures for database sessions, mock clients

**Integration Testing:**
- `tests/integration/test_e2e_flow.py` - Full flow from Slack command to Cline execution
- Docker-based testing with test PostgreSQL instance
- Mock Cline Core service for deterministic testing

**Testing Coverage Requirements:**
- Minimum 80% code coverage
- All critical paths covered (run creation, event streaming, error handling)
- Edge case testing for malformed Slack payloads, network failures

[Implementation Order]
Logical sequence of implementation to minimize conflicts and ensure successful integration.

**Step 1: Project Foundation**
- Create project structure with directories and empty files
- Set up Docker development environment with PostgreSQL
- Configure basic FastAPI app with health endpoints
- Add logging and configuration management

**Step 2: Database Layer**
- Implement SQLAlchemy models for Project and Run entities
- Set up database connection and session management
- Create basic database utilities and connection testing

**Step 3: Slack Gateway Module**
- Implement webhook signature verification
- Create HTTP endpoints for `/slack/events` and `/slack/interactivity`
- Add Slack command parsing and validation
- Test with ngrok tunnel to real Slack workspace

**Step 4: gRPC Integration Layer**
- Copy and adapt Cline proto files for Python
- Generate gRPC client code and create wrapper classes
- Implement message translation between domain models and proto
- Create mock Cline Core service for testing

**Step 5: Execution Engine Module**
- Build gRPC client with connection management
- Implement event streaming and error handling
- Add retry logic and graceful degradation
- Test against mock and real Cline Core instances

**Step 6: Run Orchestrator Module**
- Implement run lifecycle management (create, start, update, complete)
- Add event handling and database persistence
- Create channel-to-repository mapping logic
- Integrate with Execution Engine for run delegation

**Step 7: Slack Integration Completion**
- Implement Slack Web API client for posting messages
- Add progress update posting to Slack threads
- Create interactive elements (cancel buttons)
- Test full end-to-end flow with real Slack workspace

**Step 8: Production Readiness**
- Add comprehensive error handling and logging
- Implement graceful shutdown and cleanup
- Add monitoring endpoints and health checks
- Create production Docker configuration and deployment documentation
