# Implementation Plan

[Overview]
Build a professional ChatGPT-style chat experience (dedicated `/chat` page) using shadcn/Tailwind reusable components, while keeping the existing streaming backend and fixing auto-scroll/jank.

The current chat implementation (`ChatPanel`) is functional but has UX issues (finicky SSE parsing, unconditional auto-scroll causing irritating jumps, and a “dashboard card chat” layout that doesn’t feel like ChatGPT). The goal is to create a polished, production-grade chat UI with:

- A dedicated **Chat page** (`/chat`) accessible from Dashboard
- **ChatGPT-like empty state**: only input + prompt suggestions are visible initially
- After first message, the UI transitions to a classic chat transcript layout with **sticky input at bottom**
- Correct, predictable scrolling: **auto-scroll only when the user is already near the bottom**, otherwise preserve scroll position and show a “Scroll to bottom” affordance
- Reusable component approach: prefer shadcn/ui primitives and (optionally) adopt open-source shadcn chat building blocks (e.g., `shadcn-chatbot-kit` patterns) instead of bespoke styling

This work fits the existing architecture:
- Backend already persists conversation state in `conversations` (`ConversationModel.state_json`) keyed by `channel_id` and `thread_ts`
- Backend already supports streaming via `POST /api/chat` (SSE)
- Backend already supports transcript reload via `GET /api/chat/thread/{thread_id}`

We will also introduce a **conversation list** concept on the frontend (left sidebar) backed by a small new backend endpoint to list dashboard chat threads.

[Types]
Add lightweight backend and frontend types for conversation/thread listing and for richer chat UI state.

Backend (Pydantic) additions:

1) `backend/schemas/chat.py`

```py
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    thread_id: str
    channel_id: str
    project_id: Optional[UUID] = None
    updated_at: datetime
    message_count: int

    # derived from state_json
    title: str  # first user message or fallback
    last_message_preview: str
```

2) `backend/schemas/chat.py` response wrapper:

```py
class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]
```

Frontend (TypeScript) additions:

1) `frontend/src/types/chat.ts`

```ts
export interface ConversationSummary {
  threadId: string;
  channelId: string;
  projectId?: string;
  updatedAt: string;
  messageCount: number;
  title: string;
  lastMessagePreview: string;
}

export interface ChatRouteParams {
  threadId?: string;
}

export type ChatMessageRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  createdAt?: string;
}
```

2) Update `frontend/src/hooks/useChatStream.ts` internal state types to interop with `ChatMessage` above (or re-export).

[Files]
Restructure the frontend chat into a dedicated page, add conversation listing support, and improve scroll + SSE parsing.

New files:
- `frontend/src/pages/Chat.tsx`
  - Dedicated ChatGPT-style page layout
  - Empty state (center input + suggestions)
  - Transcript mode (message list + sticky input)
- `frontend/src/types/chat.ts`
  - Conversation summary types
- `frontend/src/hooks/useAutoScroll.ts`
  - Scroll anchoring logic (only auto-scroll when near bottom)
  - Exposes `isAtBottom`, `scrollToBottom`, `onUserScroll`
- `frontend/src/hooks/useSseStream.ts`
  - Robust SSE parsing using an internal buffer to handle partial frames
  - Exposes parsed AG-UI events to the chat hook
- `frontend/src/hooks/useConversations.ts`
  - Fetch and cache conversation list from backend
- `frontend/src/components/chat/ChatEmptyState.tsx`
  - ChatGPT-style landing UI (prompt suggestions)
- `frontend/src/components/chat/ChatTranscript.tsx`
  - Message list + tool indicators + scroll container
- `frontend/src/components/chat/ChatComposer.tsx`
  - Input area (Textarea + send button) styled like ChatGPT

Backend new/modified files:
- `backend/schemas/chat.py` (new)
- `backend/modules/chat/routes.py` (modify)
  - Add conversation list endpoint

Modified files:
- `frontend/src/App.tsx`
  - Add route: `/chat` and optional `/chat/:threadId`
- `frontend/src/pages/Dashboard.tsx`
  - Replace embedded ChatPanel with a CTA card/button linking to `/chat`
- `frontend/src/components/Sidebar.tsx`
  - Add `Chat` nav item pointing to `/chat`
  - Add a “Recent conversations” sub-section under Chat (populated via API)
- `frontend/src/api/client.ts`
  - Add methods:
    - `getChatThreads()` → GET `/api/chat/threads`
    - `getChatThread(threadId)` → GET `/api/chat/thread/{threadId}`
- `frontend/src/components/chat/ChatPanel.tsx`
  - Deprecate or simplify (kept for reference or used by ChatTranscript)
  - Remove unconditional `scrollIntoView` behavior

Optional new shadcn components (added via `npx shadcn@latest add ...`):
- `frontend/src/components/ui/scroll-area.tsx`
- `frontend/src/components/ui/dropdown-menu.tsx`
- `frontend/src/components/ui/tooltip.tsx`

Backend new endpoint (routes):
- `GET /api/chat/threads`
  - Returns recent `ConversationModel` rows for `channel_id="dashboard"` ordered by `updated_at desc`
  - Derives `title` and `lastMessagePreview` from `state_json.messages`

[Functions]
Introduce robust streaming parsing and controlled scroll behavior; add conversation listing.

Frontend new functions/hooks:

1) `useSseStream()` — `frontend/src/hooks/useSseStream.ts`
- Signature:
  ```ts
  export function useSseStream(): {
    stream: (response: Response, onEvent: (event: any) => void) => Promise<void>;
  }
  ```
- Responsibilities:
  - Read `response.body.getReader()`
  - Maintain a string buffer
  - Split by `\n\n` SSE frame delimiter
  - For each frame, extract concatenated `data:` lines
  - JSON.parse the payload and emit typed events

2) `useAutoScroll()` — `frontend/src/hooks/useAutoScroll.ts`
- Signature:
  ```ts
  export function useAutoScroll(opts: { thresholdPx?: number }): {
    containerRef: React.RefObject<HTMLDivElement>;
    isAtBottom: boolean;
    scrollToBottom: (behavior?: ScrollBehavior) => void;
    onScroll: () => void;
  }
  ```
- Responsibilities:
  - Track whether the user is near bottom
  - When new assistant tokens arrive, auto-scroll only if `isAtBottom`
  - Avoid “scroll down a bit” after user presses send

3) `useConversations()` — `frontend/src/hooks/useConversations.ts`
- Fetch `/api/chat/threads` and cache in state

Frontend modified function:

4) `useChatStream.sendMessage()` — `frontend/src/hooks/useChatStream.ts`
- Change behavior:
  - Do not rely on `messages` closure for request payload (avoid stale state)
  - Use a local snapshot: `const history = getLatestMessages()`
  - Use robust SSE parsing via `useSseStream()`
  - Set `threadId` on first send (route param + session storage)

Backend new functions:

5) `list_threads()` — `backend/modules/chat/routes.py`
- Signature:
  ```py
  @router.get("/threads")
  async def list_threads(session: AsyncSession = Depends(get_session)) -> ConversationListResponse:
      ...
  ```
- Responsibilities:
  - Query `ConversationModel` where `channel_id == "dashboard"`
  - Order by `updated_at desc`
  - Limit (e.g., 50)
  - Convert state_json → derived title/preview

[Classes]
No major new backend classes beyond Pydantic schemas; introduce a few small React components.

New frontend components:
- `ChatPage` (`frontend/src/pages/Chat.tsx`)
  - Layout + state machine:
    - `mode = "empty" | "chat"`
    - `empty` when no messages
    - `chat` when a thread has content
- `ChatEmptyState` (`frontend/src/components/chat/ChatEmptyState.tsx`)
  - Prompt suggestions (buttons)
- `ChatTranscript` (`frontend/src/components/chat/ChatTranscript.tsx`)
  - Scrollable transcript area
  - “Scroll to bottom” button when user not at bottom
- `ChatComposer` (`frontend/src/components/chat/ChatComposer.tsx`)
  - ChatGPT-like composer styling

Modified frontend component:
- `Sidebar` (`frontend/src/components/Sidebar.tsx`)
  - Add `Chat` section with optional list of conversation links

[Dependencies]
Add shadcn/ui components (and their Radix dependencies) for a polished chat experience.

Planned additions (exact versions resolved by shadcn installer / npm):
- `@radix-ui/react-scroll-area` (for transcript scroll container)
- `@radix-ui/react-dropdown-menu` (optional for conversation actions)
- `@radix-ui/react-tooltip` (optional)

Optional adoption of external reusable blocks:
- Reference implementation patterns from **shadcn-chatbot-kit** (open-source) for:
  - Prompt suggestions
  - Auto-scroll with manual override
  - Composer layout

We will NOT adopt Vercel AI’s `useChat` or any server runtime from that project; we only borrow UI patterns/components.

[Testing]
Validate the new chat UX with manual UI testing and a minimal set of unit/integration checks.

Frontend:
- Verify empty state shows only input + suggestions
- After sending first message:
  - route transitions to `/chat/:threadId`
  - transcript renders and streams tokens smoothly
- Scroll behavior:
  - sending does not cause small “jump”
  - auto-scroll only when near bottom
  - if user scrolls up during generation, the view remains anchored
  - show a “Scroll to bottom” button when not at bottom
- SSE parsing robustness:
  - handle partial frames without JSON parse errors

Backend:
- `GET /api/chat/threads` returns expected list and derived fields

[Implementation Order]
Implement frontend page/UX foundation first, then integrate conversation listing.

1. Add `/chat` and `/chat/:threadId` routes in `frontend/src/App.tsx`.
2. Create `frontend/src/pages/Chat.tsx` with empty state → transcript transition.
3. Implement `useSseStream` (buffered SSE parsing) and refactor `useChatStream` to use it.
4. Implement `useAutoScroll` and integrate into transcript rendering to remove scroll “jank”.
5. Build `ChatEmptyState`, `ChatTranscript`, `ChatComposer` components using shadcn primitives.
6. Update Dashboard to link to `/chat` instead of embedding chat card.
7. Add backend `GET /api/chat/threads` and frontend `useConversations`.
8. Update Sidebar: add Chat nav item + recent conversation list under Chat.
9. Manual QA pass for streaming, scroll behavior, and navigation.
