# Architecture Scope – Cline × Slack Runner

## 1. Context

We want to let developers trigger **Cline** runs directly from **Slack**, see progress there, and optionally link to their Git repos/PRs.

At a high level:

- Slack is the **UI and interaction surface**.
- Our Backend is the **orchestrator/brain**.
- A separate Runner service wraps **Cline core/CLI** and executes tasks in isolated environments (containers or processes).
- Git providers (GitHub/GitLab/etc.) are **integrations**, not the core of v1.

This document defines what we’re building in v1, what we’re not, and the architectural boundaries we care about.

---

## 2. Goals

### 2.1 Product goals (MVP)

- From Slack, a user can:
  - Run `/cline run <task>` in a mapped channel.
  - See a run start, progress updates, and completion status in the same Slack thread.
- Backend creates and tracks **Run** entities.
- Runner:
  - Clones a repo at a given ref (branch/commit).
  - Runs a “task” via Cline (or a mock agent for early testing).
  - Streams progress events back to Backend.
- All communication between Backend and Runner uses clean, documented APIs.

### 2.2 Engineering goals

- Clear separation:
  - **Slack App** = UX / wiring to Slack.
  - **Backend** = multi-tenant brain + Slack integration + run orchestration.
  - **Runner** = execution layer + Cline wrapper.
- Minimal but solid API contracts between Backend and Runner.
- Easy to:
  - Swap out Cline for another engine later.
  - Add non-Slack entrypoints (e.g. web UI) in future without changing Runner.

---

## 3. Non-goals (for MVP)

- No complex multi-step workflows like “approve patch and auto-merge”.
- No per-user repo permissions management (we assume the backend/runner has access).
- No fully featured dashboard UI:
  - Optional later, lightweight APIs now.
- No support for:
  - Multiple Git providers per tenant with granular configuration.
  - Big workspace admin flows (billing, quotas, etc.).
- No guarantees around long-running heavy tasks > 15–20 minutes in v1.

---

## 4. MVP Scope – Vertical Slice

MVP is a single **vertical slice**:

> `/cline run <task>` in one Slack channel → one run on a single repo/branch → progress streamed back to Slack.

Concretely:

- **Slack:**
  - One slash command: `/cline run <task>`.
  - Channel → repo mapping is static config or a simple DB table.
  - All updates appear in the same thread as the command.

- **Backend:**
  - Receives Slack events, validates, resolves channel → repo mapping.
  - Creates a Run record in DB.
  - Calls Runner `POST /api/runs`.
  - Subscribes to Runner events (SSE/WS).
  - For each event:
    - Updates DB.
    - Posts/updates Slack thread.

- **Runner:**
  - Exposes:
    - `POST /api/runs`
    - `GET /api/runs/:id`
    - `GET /api/runs/:id/events` (SSE) or WS equivalent.
    - `POST /api/runs/:id/cancel`.
  - For MVP:
    - Can use a mock “agent” that simulates steps and logs.
    - Real Cline integration comes once plumbing is stable.

---

## 5. Constraints & Assumptions

- Initial deployment can be a single region, single environment (e.g. “dev”).
- Authentication between Backend ↔ Runner:
  - Simple shared secret or service-level API key for v1.
- Postgres is available for Backend for persistent run tracking.
- Runner can assume:
  - It has access to required Git repos (via SSH key or token).
- Slack workspace:
  - We’ll start with **one** workspace, manually installed (no Marketplace).

---

## 6. Future-facing considerations (but not in MVP)

- Multiple Slack workspaces (multi-tenant).
- Mapping PRs → runs automatically via Git webhooks.
- Dashboard UI to view runs outside Slack.
- Policy-driven limits: per-tenant max concurrent runs, rate limiting.
- Artifact management and download (e.g. diff bundles, logs).
