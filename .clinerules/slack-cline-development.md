## Brief overview

Project-specific rules for developing slack-cline, a Slack bot that integrates Cline's AI coding capabilities via CLI subprocess calls. The primary goal is Slack integration, with the dashboard serving as a testing and debugging tool.

## Service management

- Never automatically start or restart Docker services (docker-compose) or frontend dev server (npm run dev)
- Always ask the user to run these commands themselves
- When changes require a restart, inform the user and provide the exact command to run
- Example: "Please restart the backend: `docker-compose restart backend`"

## Tech stack preferences

- **Backend**: Python FastAPI with async/await patterns
- **Database**: PostgreSQL with SQLAlchemy async
- **Frontend**: React + Vite + TypeScript + Tailwind CSS
- **Validation**: Pydantic v2 with `ConfigDict` for model validation
- **Logging**: Structured logging with structlog
- **Deployment**: Docker Compose for local development

## Architecture patterns

- Modular backend structure: separate modules for concerns (slack_gateway, orchestrator, execution_engine, dashboard)
- CLI subprocess integration over gRPC (proven pattern from GitHub Actions)
- Direct function calls when possible instead of internal HTTP requests to avoid stream consumption issues
- Service layer pattern: routes call services, services handle business logic
- Singleton services with dependency injection

## Slack-first development approach

- Slack is the primary production interface
- Dashboard is for testing, debugging, and configuration management
- Admin Panel tests the full Slack integration flow without requiring Slack setup
- Always validate via dashboard before moving to Slack integration
- Documentation should emphasize Slack as the goal, dashboard as the development tool

## Code organization

- Place Pydantic schemas in `backend/schemas/`
- Place database models in `backend/models/`
- Place service logic in `backend/modules/<module>/service.py`
- Place API routes in `backend/modules/<module>/routes.py`
- Frontend components in `frontend/src/components/`
- Frontend pages in `frontend/src/pages/`
- Shared types in `frontend/src/types/index.ts`

## PowerShell compatibility

- User is on Windows with PowerShell
- Use PowerShell syntax for commands, not bash (`;` not `&&`)
- Example: `cd path; command` not `cd path && command`
- Use PowerShell cmdlets when appropriate: `New-Item`, `Remove-Item`, etc.

## Error handling patterns

- Always handle UUID serialization properly (use Pydantic's `UUID` type, not `str`)
- Avoid reading request body multiple times (stream consumption)
- Use try-except blocks with specific error types
- Log errors with context using structlog
- Return meaningful error messages to frontend

## Documentation standards

- Create comprehensive guides (GETTING_STARTED, feature guides, debugging guides)
- Include both dashboard and Slack workflows
- Provide troubleshooting sections with common issues and solutions
- Include quick reference commands
- Emphasize E2E testing workflows

## Testing approach

- Dashboard testing before Slack integration
- Use Admin Panel to simulate Slack commands
- Verify in database and Runs page
- Check backend logs for detailed execution trace
- Test both dashboard flow and Slack flow independently

## API design

- RESTful endpoints for dashboard (`/api/*`)
- Separate Slack webhook endpoints (`/slack/*`)
- Use Pydantic schemas for request/response validation
- CORS configured for frontend access
- Health check endpoints for monitoring
