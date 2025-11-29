# Architecture Scope – Cline × Slack (Single Backend + Cline gRPC)

## 1. Context

We want developers to trigger **Cline** runs directly from **Slack**, see progress there, and optionally tie runs to Git repos/PRs.

We are choosing a **single backend service** that:

* Exposes HTTP endpoints for Slack (Events + Interactivity).
* Orchestrates runs and persists them in a database.
* Talks to **Cline Core over gRPC** via an **Execution Engine** module.

**Cline Core** itself runs as a **gRPC server** (in a sidecar process/container or separate service in the same VPC).

This replaces the earlier idea of a separate “Runner HTTP microservice” and keeps the boundary as an **internal module + gRPC API** instead.

---

## 2. Goals

### 2.1 Product goals (MVP)

For the first version:

* From Slack, a user can:

  * Run `/cline run <task>` in a mapped channel.
  * See a run start, progress updates, and completion status in the same thread.
* Backend:

  * Stores and tracks **Run** entities.
  * Talks to Cline Core via gRPC to execute tasks.
* Cline Core:

  * Receives a repo ref + task description.
  * Executes the task (mock at first, real Cline later).
  * Streams progress/events back to the backend via gRPC streams.

### 2.2 Engineering goals

* **Single deployable backend** that:

  * Is the *only* HTTP-exposed service.
  * Internally has clear modules:

    * Slack Gateway
    * Run Orchestrator
    * Execution Engine (gRPC client to Cline Core)
* **Strong internal boundary** between:

  * **Orchestration** (business logic, Slack, DB)
  * **Execution** (Cline, repos, tools)
* Make it easy to:

  * Swap Cline out for another engine later.
  * Move Execution Engine into its own service if needed (keeping the same API contract).

---

## 3. MVP Scope – Vertical Slice

MVP = **one vertical slice**:

> `/cline run <task>` in one Slack channel → one run on a single repo/branch → progress streamed back to Slack.

Concretely:

### 3.1 Slack

* One slash command:
  `/cline run <task>`
* Channel → repo mapping:

  * Static config file or a simple DB table (`projects`).
* All updates appear in the **thread** where the command was invoked:

  * “Run started…”
  * “Step 1/3: Cloning repo…”
  * “Run succeeded/failed – summary…”

### 3.2 Backend

* Receives Slack events via HTTP.
* Resolves `channel` → `{ repo_url, default_ref }` (e.g. `main`).
* Creates a **Run** record in Postgres with:

  * `status = QUEUED`
* Uses **Execution Engine** to:

  * Start a run (gRPC unary RPC: `StartRun`).
  * Subscribe to events (gRPC streaming RPC: `StreamEvents`).
* For each event:

  * Updates the Run in DB.
  * Posts/updates Slack thread via Slack API.

### 3.3 Cline Core (gRPC server)

* Exposes a gRPC service (e.g. `ClineRunner`) with:

  * `StartRun`
  * `GetRun`
  * `StreamEvents` (server-side stream)
  * `CancelRun`
* For MVP:

  * May be a **mock implementation** first (fake steps/logs, no real edits).
  * Later, wired to **real Cline Core** and actual repo operations.

---

## 4. Logical Boundaries (Inside the Backend)

### 4.1 Slack Gateway

**Responsibilities**

* Verify Slack request signatures.
* Handle:

  * Slash commands (e.g. `/cline run <task>`).
  * Interactive actions (buttons like “Cancel run”).
* Map Slack events into internal commands/event types:

  * `StartRunCommand`
  * `CancelRunCommand`

**Non-responsibilities**

* No direct calls to Cline Core.
* No repo or execution details.

It simply hands off to the **Run Orchestrator**.

---

### 4.2 Run Orchestrator

**Responsibilities**

* Channel → repo mapping:

  * Uses `projects` table or config to find `repo_url` and `default_ref`.
* **Run lifecycle**:

  * Creates/updates `runs` in DB:

    * `QUEUED → RUNNING → SUCCEEDED/FAILED/CANCELLED`
* Talks to **Execution Engine**:

  * `startRun(repo, task, limits) → cline_run_id`
  * `streamEvents(cline_run_id)` and consume events.
  * `cancelRun(cline_run_id)` on request.

**Outputs**

* DB state changes.
* Slack updates:

  * Orchestrator calls Slack Gateway helpers to send messages to the right channel/thread.

---

### 4.3 Execution Engine

**Responsibilities**

* The **only** module that knows:

  * How to talk to **Cline Core gRPC**.
  * The `ClineRunner` proto contract.
* Translates:

  * Domain inputs (`TaskSpec`, `RepoRef`, limits) → `StartRunRequest`.
  * gRPC `RunEvent` messages → internal `RunEvent`/domain events.

**Why this layer exists**

* Allows **unit testing** Orchestrator by mocking the Execution Engine.
* Keeps gRPC and Cline-specific details out of business logic.
* Makes it trivial to:

  * Move Execution Engine into its own service later,
  * Or swap Cline for another engine, as long as Execution Engine implements the same interface.

---

## 5. Non-goals (MVP)

The following are **explicitly out of scope** for MVP:

* Complex workflows:

  * Multi-step approvals, “auto-merge if green”, etc.
* Per-user repo auth/ACL semantics:

  * We assume the backend/engine has sufficient repo access.
* Full-featured web dashboard:

  * No separate UI beyond Slack.
* Advanced multi-git-provider routing:

  * MVP can support a single provider or a simple configuration.
* Enterprise auth / SSO:

  * Slack workspace auth is sufficient for now.
* Hard guarantees on **long-running** tasks:

  * Tasks > 15–20 minutes may be best-effort in v1.

---

## 6. Future-Facing Considerations

These inform today’s design but are **not** built in MVP:

### 6.1 Separate Runner Microservice

* Execution Engine could be extracted into its own service:

  * Backend → Runner via HTTP/gRPC.
  * The gRPC contract you define now (`ClineRunner`) becomes the external API.
* Benefits:

  * Independent scaling for execution-heavy work.
  * Stronger fault isolation.

### 6.2 Multi-Tenant Support

* Support multiple Slack workspaces as tenants.
* Per-tenant:

  * Repo mappings.
  * Usage quotas and rate limits.
  * Separate secrets/tokens.

### 6.3 Web UI / Dashboard

* Additional frontend talking to the same Backend:

  * View runs across channels/workspaces.
  * Filter by repo, status, user.
  * Inspect logs and artifacts.

### 6.4 Additional Tools & Capabilities

* Cline Core can orchestrate more tools:

  * Test runners, static analyzers, security scanners.
* Backend stays agnostic:

  * Just shows “what Cline did” and surfaces summaries/diffs.

---

## 7. Summary

* **One backend** handles Slack, orchestration, and DB.
* **Cline Core** is accessed only via a clean **gRPC Execution API**.
* MVP focuses on a single, solid vertical slice:

  * `/cline run <task>` → run on one repo → progress in Slack.
* The internal boundaries (Slack Gateway, Orchestrator, Execution Engine) are designed so you can:

  * Scale,
  * Split services,
  * Or swap engines later without major rewrites.
