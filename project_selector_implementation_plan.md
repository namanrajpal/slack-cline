# Implementation Plan: Dashboard Project Selector

## [Overview]
Add project selector dropdown to dashboard chat interface for explicit project context.

This implementation adds a project selector dropdown to the Chat.tsx interface, allowing dashboard users to explicitly choose which project they're discussing. The selected project bypasses the LLM classifier and is passed directly to the backend agent service. This feature is dashboard-specific and cleanly decoupled from core agent logic, maintaining compatibility with Slack's workflow while laying the foundation for future file mention features (@backend/module.py).

Key architectural principles:
- Dashboard-specific context (project selection) isolated from core AgentService logic
- Slack flow remains unchanged (no access to projectId field)
- Conditional logic: if projectId provided → use directly, else → use LLM classifier
- Project selection tied to conversation lifecycle (not persisted globally)

## [Types]
Add new type definitions and extend existing schemas for project selection context.

**Frontend Types (frontend/src/types/index.ts):**
```typescript
// No changes needed - Project type already exists
// ChatMessage type is in chat.ts, which already exists
```

**Backend Schema Extensions (backend/schemas/agui.py):**
```python
class ChatRequest(BaseModel):
    """Chat request structure (method-based routing)."""
    model_config = ConfigDict(populate_by_name=True)
    
    method: Optional[str] = None
    thread_id: Optional[str] = Field(default=None, alias="threadId")
    run_id: Optional[str] = Field(default=None, alias="runId")
    messages: Optional[list[ChatMessage]] = None
    state: Optional[dict] = None
    
    # NEW: Dashboard-specific project context (Slack won't use this)
    project_id: Optional[str] = Field(default=None, alias="projectId")  # UUID as string
```

## [Files]
Detailed breakdown of file modifications and deletions.

**Files to Delete:**
- `frontend/src/components/chat/ChatPanel.tsx` - Unused old component, replaced by Chat.tsx blocks.so design

**Files to Modify:**

1. **frontend/src/pages/Chat.tsx**
   - Add state for `selectedProjectId: string | null`
   - Add state for `projects: Project[]`
   - Add `useEffect` to fetch projects from `/api/projects` on mount
   - Add project selector dropdown in `renderComposer()` after Settings button
   - Reset selected project when creating new conversation (+ button)
   - Pass `selectedProjectId` to `sendMessage()` calls

2. **frontend/src/hooks/useChatStream.ts**
   - Modify `sendMessage()` to accept optional `projectId?: string` parameter
   - Include `projectId` in POST request body to `/api/chat`

3. **backend/schemas/agui.py**
   - Add `project_id` field to `ChatRequest` schema (see Types section)

4. **backend/modules/chat/routes.py**
   - Extract `project_id` from `ChatRequest`
   - Pass `project_id` to `agent_service.handle_message_streaming()`

5. **backend/modules/agent/service.py**
   - Modify `handle_message_streaming()` signature to accept `project_id: Optional[str] = None`
   - Pass `project_id` to `_get_or_create_state()`
   - Modify `_get_or_create_state()` to accept `project_id: Optional[str] = None`
   - Add conditional logic: if `project_id` provided, fetch project directly; else use classifier

**Files to Create:**
- None (all modifications to existing files)

## [Functions]
Detailed breakdown of function modifications.

**Frontend Functions:**

1. **Chat.tsx: New state and hooks**
   - `const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)`
   - `const [projects, setProjects] = useState<Project[]>([])`
   - `useEffect(() => { loadProjects(); }, [])` - Fetch projects on mount
   - `const loadProjects = async () => { ... }` - Fetch from `/api/projects`

2. **Chat.tsx: Modified renderComposer()**
   - Add project selector dropdown between Settings and Send button
   - Use shadcn Select component for consistency
   - Options: "Auto-detect" (null) + list of projects
   - Display project name in dropdown

3. **useChatStream.ts: Modified sendMessage()**
   - **Current signature:** `sendMessage(text: string)`
   - **New signature:** `sendMessage(text: string, projectId?: string | null)`
   - Include `projectId` in POST body: `{ threadId, messages, projectId }`

**Backend Functions:**

1. **chat/routes.py: Modified chat_endpoint()**
   - Extract `project_id` from request: `project_id = request.project_id`
   - Pass to agent service: `agent_service.handle_message_streaming(..., project_id=project_id)`

2. **agent/service.py: Modified handle_message_streaming()**
   - **Current signature:** `handle_message_streaming(channel_id, thread_ts, user_id, text, session)`
   - **New signature:** `handle_message_streaming(channel_id, thread_ts, user_id, text, session, project_id: Optional[str] = None)`
   - Pass `project_id` to `_get_or_create_state()`

3. **agent/service.py: Modified _get_or_create_state()**
   - **Current signature:** `_get_or_create_state(channel_id, thread_ts, user_id, session, user_question)`
   - **New signature:** `_get_or_create_state(channel_id, thread_ts, user_id, session, user_question, project_id: Optional[str] = None)`
   - **New logic:**
     ```python
     if project_id:
         # Dashboard provided explicit project - use directly
         try:
             project_uuid = UUID(project_id)
             result = await session.execute(select(ProjectModel).filter(ProjectModel.id == project_uuid))
             project = result.scalar_one_or_none()
             if not project:
                 logger.warning(f"Project {project_id} not found, falling back to classifier")
                 # Fall through to classifier logic
             else:
                 logger.info(f"Using dashboard-selected project: {project.name}")
         except ValueError:
             logger.error(f"Invalid project_id format: {project_id}")
             # Fall through to classifier logic
     
     if not project_id or not project:
         # Slack or no project specified - use LLM classifier
         project = await classify_project(...)
     ```

## [Classes]
No new classes or class modifications required.

All changes are function-level modifications to existing classes:
- `ChatRequest` Pydantic model extended with new field (not a class structure change)
- `AgentService` methods modified (no new classes)

## [Dependencies]
No new dependencies required.

All required dependencies already exist:
- Frontend: React, shadcn/ui Select component, apiClient
- Backend: Pydantic, UUID, SQLAlchemy, existing models

**Verification Commands:**
```powershell
# Verify shadcn Select is available
Get-Content "frontend/src/components/ui/select.tsx" | Select-Object -First 5

# Verify apiClient has getProjects
Get-Content "frontend/src/api/client.ts" | Select-String -Pattern "getProjects"
```

## [Testing]
Testing strategy for project selector feature.

**Manual Testing Steps:**

1. **Frontend - Project Selector UI**
   - Open `/chat` in browser
   - Verify project selector appears after Settings button
   - Verify "Auto-detect" is default option
   - Verify all projects from `/api/projects` appear in dropdown
   - Select a project, verify it's highlighted
   - Start new chat (+ button), verify selector resets to "Auto-detect"

2. **Frontend - API Integration**
   - Open browser DevTools Network tab
   - Send message with "Auto-detect" selected
   - Verify POST `/api/chat` body: `{ threadId, messages, projectId: null }`
   - Select a specific project
   - Send message
   - Verify POST body includes: `{ threadId, messages, projectId: "uuid-here" }`

3. **Backend - Project Selection Logic**
   - Check backend logs for "Using dashboard-selected project: {name}"
   - Verify agent uses correct workspace path
   - Test with no projects configured - verify error handling
   - Test with invalid project_id - verify fallback to classifier

4. **Backend - Slack Compatibility**
   - Test Slack @mention (if Slack is configured)
   - Verify Slack flow still works (project_id not sent from Slack)
   - Verify LLM classifier is used for Slack messages

5. **Conversation Persistence**
   - Start chat with Project A, send message
   - Refresh page, load same thread
   - Verify thread loads correctly
   - Note: Project selection is per-conversation, stored in DB

**Test Cases:**

| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| Auto-detect with 1 project | Select "Auto-detect", send message | Uses first project (current behavior) |
| Auto-detect with multiple | Select "Auto-detect", send message | LLM classifier selects best project |
| Explicit project selection | Select specific project, send message | Uses selected project, skips classifier |
| Invalid project ID | Manually send invalid UUID | Falls back to classifier gracefully |
| No projects configured | Open chat with no projects | Shows error message |
| Slack integration | Send Slack @mention | Slack flow unaffected, uses classifier |

## [Implementation Order]
Step-by-step sequence to minimize conflicts and ensure successful integration.

1. **Backend Schema Extension (foundation)**
   - Modify `backend/schemas/agui.py` to add `project_id` field to `ChatRequest`
   - This is backward-compatible (optional field)

2. **Backend Service Logic (core)**
   - Modify `backend/modules/agent/service.py`:
     - Update `handle_message_streaming()` signature
     - Update `_get_or_create_state()` signature and logic
   - Add conditional project selection logic

3. **Backend Route Handler (integration)**
   - Modify `backend/modules/chat/routes.py`:
     - Extract `project_id` from request
     - Pass to agent service

4. **Test Backend Changes**
   - Use curl or Postman to test `/api/chat` with `projectId` field
   - Verify logs show "Using dashboard-selected project" or classifier usage
   - Verify Slack flow still works (if available)

5. **Frontend Hook Modification (data layer)**
   - Modify `frontend/src/hooks/useChatStream.ts`:
     - Update `sendMessage()` signature
     - Include `projectId` in POST body

6. **Frontend UI Implementation (presentation)**
   - Modify `frontend/src/pages/Chat.tsx`:
     - Add state for projects and selectedProjectId
     - Add useEffect to fetch projects
     - Add project selector dropdown in renderComposer()
     - Wire up selection handling
     - Pass projectId to sendMessage()

7. **Cleanup Redundant Code**
   - Delete `frontend/src/components/chat/ChatPanel.tsx`
   - Verify no imports remain

8. **End-to-End Testing**
   - Test complete flow: select project → send message → verify backend uses correct project
   - Test auto-detect mode
   - Test conversation persistence
   - Test new chat creation (+ button)

9. **Documentation Update (optional)**
   - Update `docs/user-guide/dashboard.md` with project selector feature
   - Add screenshots of UI

**Critical Dependencies:**
- Step 5 depends on Steps 1-4 (backend must accept projectId first)
- Step 6 depends on Step 5 (hook must support projectId before UI uses it)
- Step 7 can happen anytime after Step 6
- Step 8 must be last (validates entire integration)
