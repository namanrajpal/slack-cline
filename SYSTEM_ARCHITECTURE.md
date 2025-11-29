# System Architecture – Cline × Slack (Single Backend + Cline gRPC)

## 1. Components Overview

We have four primary elements:

1. **Slack App (UI surface)**

   * Slash command + bot user living in the user’s Slack workspace.

2. **Backend Service** (single deployable)

   * **Slack Gateway**
   * **Run Orchestrator**
   * **Execution Engine** (gRPC client)
   * **Postgres** integration

3. **Cline Core (gRPC)**

   * A gRPC server that executes runs and streams events.

4. **External services**

   * Git provider(s): e.g., GitHub/GitLab (for repo clones / fetch).

The backend is the *only* HTTP-exposed component; everything else is internal.

---

## 2. High-Level Diagram

```mermaid
flowchart LR
  subgraph Slack["Slack Workspace"]
    U[Developer] -->|/cline run <task>| SA[Slack App / Bot]
  end

  subgraph Backend["Backend Service"]
    SG[Slack Gateway<br/>(HTTP)] --> ORCH[Run Orchestrator]
    ORCH --> DB[(Postgres)]
    ORCH --> EXE[Execution Engine<br/>(gRPC client)]
  end

  subgraph Cline["Cline Core"]
    CC[ClineRunner gRPC Server]
  end

  EXE -->|gRPC| CC
  CC -->|clone/fetch| GH[Git Provider]

  SA -->|Events & Interactivity| SG
  ORCH -->|Slack Web API calls| SA
```

---

## 3. Component Responsibilities

### 3.1 Slack App

**Responsibilities**

* Provide the user-facing interface:

  * Slash command: `/cline run <task>`.
  * Bot user for posting messages & replies.
* Deliver events to the backend:

  * Slash commands → backend endpoint.
  * Interactive components (buttons, etc.) → backend endpoint.

**Key Config**

* Slash command:

  * Command: `/cline`
  * Request URL: `https://<backend>/slack/events`
* Interactivity:

  * Request URL: `https://<backend>/slack/interactivity`
* OAuth (optional/multi-tenant later):

  * Redirect URL: `https://<backend>/slack/oauth/callback`

Slack stays very “dumb”: it just forwards events and renders messages.

---

### 3.2 Backend – Slack Gateway

**Responsibilities**

* Verify Slack request signatures.
* Parse:

  * Slash commands (`/cline run <task>`).
  * Interactive payloads (e.g., “Cancel run” button).
* Convert Slack payloads into internal commands:

  * `StartRunCommand`
  * `CancelRunCommand`

**Main HTTP endpoints**

* `POST /slack/events`

  * Handles slash commands and any event callbacks you subscribe to.
* `POST /slack/interactivity`

  * Handles button clicks, menus, etc.
* `GET /slack/oauth/callback` (optional)

  * OAuth flow if/when you support multiple workspaces.

Slack Gateway does *not* know about Cline or gRPC; it forwards to Run Orchestrator.

---

### 3.3 Backend – Run Orchestrator

This is the core “brain” of the application.

**Responsibilities**

* **Run creation**

  * Take `StartRunCommand` from Slack Gateway.
  * Resolve Slack channel → repository from `projects` table/config:

    * Given `slack_team_id`, `slack_channel_id` → `{ repo_url, default_ref }`.
  * Create a row in `runs` table with:

    * `status = QUEUED`
    * Slack metadata (channel, thread, user).
  * Call **Execution Engine**:

    * `startRun(repoUrl, refType, ref, task, limits)` → returns `cline_run_id`.
  * Update run with `cline_run_id` and transition to `RUNNING` when appropriate.

* **Run event handling**

  * For each active run:

    * Subscribe via Execution Engine to `streamEvents(cline_run_id)`.
  * On each event:

    * Update `runs` table (status, summary, timestamps).
    * Invoke Slack helpers to post/update messages in the correct thread.

* **Run cancellation**

  * On a cancel command (e.g., button):

    * Mark run as “cancel requested” in DB.
    * Call `ExecutionEngine.cancelRun(cline_run_id, reason)`.
    * Reflect final status based on Cline events.

**Outputs**

* Persistent state in Postgres.
* Slack messages:

  * Initial “Run started…”
  * Progress updates.
  * Final summary.

---

### 3.4 Backend – Execution Engine (gRPC Client)

The Execution Engine is a library/module inside the backend that wraps gRPC.

**Responsibilities**

* Be the **only** code that:

  * Knows about the `ClineRunner` gRPC service.
  * Translates between backend domain models and proto types.

* Provide an internal interface like:

  ```ts
  interface ExecutionEngine {
    startRun(...): Promise<{ clineRunId: string }>;
    getRun(runId: string): Promise<RunSnapshot>;
    streamEvents(runId: string, onEvent, onError): { cancel: () => void };
    cancelRun(runId: string, reason?: string): Promise<void>;
  }
  ```

* Manage:

  * gRPC channels.
  * Backoff/retry policies.
  * Converting gRPC `RunEvent` into domain events used by the Orchestrator.

**Non-responsibilities**

* No Slack knowledge.
* No DB writes.

It’s purely “ask Cline to do work and translate its responses.”

---

### 3.5 Cline Core (gRPC Server)

**Responsibilities**

* Host the `ClineRunner` gRPC service (see `EXECUTION_API_GRPC.md`).
* For each `StartRun` request:

  * Validate inputs.
  * Clone/fetch repository (via Git provider).
  * Launch Cline agent logic (mock in early dev; real Cline later).
  * Emit `RunEvent` messages on `StreamEvents` stream.
* Track run state internally, so `GetRun` and `CancelRun` work.

**Execution Environment**

* Cline Core can:

  * Spawn subprocesses.
  * Use containers/devcontainers.
  * Integrate additional tools (test runner, static analyzer, etc.).

Backend doesn’t care how Cline does the work; it just cares about gRPC responses.

---

### 3.6 External: Git Provider

**Responsibilities**

* Host the code repos Cline operates on.
* Provide access via:

  * HTTPS (PAT/token).
  * SSH (key-based).

Cline Core is responsible for:

* Authenticating to Git.
* Cloning/fetching repos as needed.

---

## 4. End-to-End Flow: `/cline run <task>`

### 4.1 Command Issued

1. Developer in Slack channel `#checkout-service` runs:

   ```text
   /cline run "Run unit tests and summarize failures"
   ```

2. Slack sends an HTTP POST to `https://<backend>/slack/events` with the slash command payload.

---

### 4.2 Slack Gateway

3. Slack Gateway:

   * Validates Slack signature.
   * Parses command:

     * Tenant (Slack team) ID.
     * Channel ID.
     * User ID.
     * Text → `task_prompt`.

4. Slack Gateway emits a `StartRunCommand` to the Orchestrator (in-process call).

5. It also sends an immediate Slack response:

   * Either ephemeral or thread message:

     * “Starting Cline run for `Run unit tests and summarize failures`…”

---

### 4.3 Orchestrator: Run Setup

6. Orchestrator:

   * Looks up `projects` table:

     * Key: `{ slack_team_id, slack_channel_id }`
     * Value: `{ repo_url, default_ref }`
   * Creates DB row in `runs`:

     * `status = QUEUED`
     * `task_prompt = "Run unit tests and summarize failures"`
     * `slack_channel_id`, `slack_thread_ts`, `tenant_id`

7. Orchestrator calls `ExecutionEngine.startRun()`:

   * Input:

     * `repoUrl = repo_url`
     * `refType = "branch"`
     * `ref = default_ref`
     * `prompt = task_prompt`
     * limits (e.g., max duration, tokens)
     * metadata (Slack IDs, etc.)

8. Execution Engine:

   * Translates to `StartRunRequest` proto.
   * Calls Cline Core’s gRPC `StartRun`.
   * Receives `run_id` (Cline’s run ID).
   * Returns `clineRunId` to Orchestrator.

9. Orchestrator:

   * Updates `runs` row with `cline_run_id`.
   * Optionally updates status to `RUNNING` once events start arriving.

---

### 4.4 Execution + Events

10. Execution Engine calls `StreamEvents(run_id)` on Cline Core and starts listening.

11. Cline Core:

    * Clones the repo.
    * Runs agent logic (e.g., run tests).
    * Streams `RunEvent` messages:

      * Status changes.
      * Steps (“Cloning repo”, “Running npm test”, etc.).
      * Logs.
      * Diffs.
      * Final summary.

12. Execution Engine:

    * For each `RunEvent`:

      * Converts proto into domain event.
      * Calls back into Orchestrator (`onRunEvent`).

13. Orchestrator:

    * Updates `runs` table accordingly:

      * Status transitions.
      * Timestamps.
      * Summary.
    * Calls Slack Gateway helper functions to:

      * Post progress updates in the original thread.
      * Post a final summary when `DONE`.

---

## 5. Persistence Model

### 5.1 `projects` Table (Channel → Repo Mapping)

Used to tie Slack channels to code repos.

* `id` (UUID or integer)
* `tenant_id` (Slack team ID or internal tenant key)
* `slack_channel_id`
* `repo_url` (e.g. `https://github.com/org/repo.git`)
* `default_ref` (e.g. `main`)
* `created_at`
* `updated_at`

> MVP: you can store this in a config file, but DB table makes it easy to manage later via UI.

---

### 5.2 `runs` Table

Tracks lifecycle of runs for auditing and UI.

* `id` (backend run id, UUID)
* `tenant_id`
* `project_id` (FK into `projects`)
* `cline_run_id` (run ID from Cline Core gRPC)
* `status`

  * `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`
* `task_prompt`
* `slack_channel_id`
* `slack_thread_ts`
* `created_at`
* `started_at`
* `finished_at`
* `summary` (short text summary; full logs can live elsewhere later)

---

## 6. Deployment Sketch

### 6.1 Local Development

Use `docker-compose`:

* `backend`:

  * Exposes HTTP (e.g., `http://localhost:8080`).
  * Connected to Postgres.
* `cline-core`:

  * Exposes gRPC (e.g., `grpc://cline-core:50051`).
* `postgres`:

  * Data store for backend.

Expose backend to Slack with ngrok:

* `ngrok http 8080`
* Use the forwarded URL as Slack’s Request URL.

---

### 6.2 Cloud (MVP)

**Backend**

* Single container image.
* Deployed to:

  * ECS, Kubernetes, or any container platform.
* Exposes:

  * HTTPS endpoint for Slack (`/slack/events`, `/slack/interactivity`).
* Connects to:

  * Managed Postgres (RDS, Cloud SQL, etc.).
  * Internal network endpoint for Cline Core gRPC.

**Cline Core**

* Deployed as:

  * Sidecar in same pod/task as Backend, or
  * Separate service in the same VPC (internal load balancer).
* Exposes:

  * gRPC on an internal-only address/port.

---

## 7. Extension Points

### 7.1 Additional Entry Points

* Web UI / Dashboard:

  * Talks to Backend via REST/GraphQL.
  * Lists runs, shows status, summaries, logs.
* CLI:

  * Could hit Backend directly (reusing the same Orchestrator).

### 7.2 Git Webhooks

* Backend exposes `/git/webhooks`.
* On PR events:

  * Post to mapped Slack channel:

    * “PR #123 opened – run `/cline run review` to have Cline review it.”

### 7.3 Scaling Out

* If execution load becomes heavy:

  * Split Execution Engine into its own microservice that implements the same gRPC contract with Cline Core, or
  * Have separate worker instances of the backend that mostly handle Execution Engine responsibilities.

---

## 8. Summary

* **Single backend** is the public face:

  * Handles Slack, orchestration, and persistence.
* **Cline Core gRPC** is a separate, internal execution engine:

  * Clones repos and runs agent tasks.
* The architecture is:

  * Simple enough for a 4-person team to ship an MVP.
  * Structured enough that you can later:

    * Add dashboards,
    * Support multiple workspaces,
    * Or split into more services without rewriting everything.
