## Brief overview

Project-specific rules for developing slack-cline, a conversational AI coding teammate built with a native Python LangGraph agent. Users interact via natural @mentions in Slack, with the dashboard serving as a testing and debugging tool.

## Service management

- Never automatically start or restart Docker services (docker-compose) or frontend dev server (npm run dev)

## Tech stack preferences

- **Backend**: Python FastAPI with async/await patterns
- **Database**: PostgreSQL with SQLAlchemy async
- **Frontend**: React + Vite + TypeScript + Tailwind CSS
- **Validation**: Pydantic v2 with `ConfigDict` for model validation
- **Logging**: Structured logging with structlog
- **Deployment**: Docker Compose for local development

## Architecture patterns

- Native LangGraph agent architecture using ReAct pattern
- Conversational model: each Slack thread is a persistent conversation
- Agent service manages conversation state and LangGraph invocation
- Tools bound to workspace paths for clean LLM interface
- Modular backend structure: separate modules for concerns (slack_gateway, agent, dashboard)
- Service layer pattern: routes call services, services handle business logic
- Singleton services with dependency injection
- State persistence via PostgreSQL (state_json field in conversations table)

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

- Follow documentation guidelines in `.clinerules/documentation-standards.md`
- Place new docs in `docs/` with proper hierarchy (getting-started/, user-guide/, architecture/, development/)
- Create implementation plans in `docs/implementation-plans/` before major features
- Update `docs/README.md` index when adding new documentation
- Include both dashboard and Slack workflows
- Provide troubleshooting sections with common issues and solutions

## Testing approach

- Dashboard testing before Slack integration
- Use Admin Panel to simulate @mention conversations
- Verify in database (conversations table with state_json)
- Check backend logs for detailed agent execution trace (tool calls, LLM responses)
- Test conversation continuity (multi-turn interactions with memory)
- Test both dashboard flow and Slack flow independently

## API design

- RESTful endpoints for dashboard (`/api/*`)
- Separate Slack webhook endpoints (`/slack/*`)
- Use Pydantic schemas for request/response validation
- CORS configured for frontend access
- Health check endpoints for monitoring
