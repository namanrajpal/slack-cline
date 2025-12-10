# System Architecture – Cline × Slack (CLI Subprocess Integration)

## 1. Components Overview

We have four primary elements:

1. **Slack App (UI surface)**

   * Slash command + bot user living in the user's Slack workspace.

2. **Backend Service** (single deployable)

   * **Slack Gateway**
   * **Run Orchestrator**
   * **Execution Engine** (CLI subprocess wrapper)
   * **Postgres** integration
   * **Cline CLI** (embedded, manages Cline Core automatically)

3. **Cline Core**

   * Managed automatically by Cline CLI
   * Executes runs and provides output streams

4. **External services**

   * Git provider(s): e.g., GitHub/GitLab (for repo clones / fetch).

The backend is the *only* HTTP-exposed component; everything else is internal.

> **Note:** This architecture uses Cline CLI subprocess calls instead of direct gRPC integration. The Cline CLI handles instance management, workspace setup, and communication with Cline Core automatically. See [FINAL_ARCHITECTURE.md](./FINAL_ARCHITECTURE.md) for the evolution from gRPC to CLI approach.

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
    ORCH --> EXE[Execution Engine<br/>(CLI subprocess)]
    EXE --> CLI[Cline CLI]
  end

  subgraph Cline["Cline Core (managed by CLI)"]
    CLI -->|manages| CC[Cline Core]
  end

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

Slack stays very "dumb": it just forwards events and renders messages.

---

### 3.2 Backend – Slack Gateway

**Responsibilities**

* Verify Slack request signatures.
* Parse:

  * Slash commands (`/cline run <task>`).
  * Interactive payloads (e.g., "Cancel run" button).
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

Slack Gateway does *not* know about Cline CLI; it forwards to Run Orchestrator.

---

### 3.3 Backend – Run Orchestrator

This is the core "brain" of the application.

**Responsibilities**

* **Run creation**

  * Take `StartRunCommand` from Slack Gateway.
  * Resolve Slack channel → repository from `projects` table/config:

    * Given `slack_team_id`, `slack_channel_id` → `{ repo_url, default_ref }`.
  * Create a row in `runs` table with:

    * `status = QUEUED`
    * Slack metadata (channel, thread, user).
  * Call **Execution Engine**:

    * `startRun(repoUrl, refType, ref, task, provider, apiKey, modelId)` → returns `{instance_address, task_id, workspace_path}`.
  * Update run with Cline instance details and transition to `RUNNING`.

* **Run event handling**

  * For each active run:

    * Subscribe via Execution Engine to `streamEvents(instance_address, workspace_path, task_id)`.
  * On each event:

    * Update `runs` table (status, summary, timestamps).
    * Invoke Slack helpers to post/update messages in the correct thread.

* **Run cancellation**

  * On a cancel command (e.g., button):

    * Mark run as "cancel requested" in DB.
    * Call `ExecutionEngine.cancelRun(instance_address, workspace_path, reason)`.
    * Reflect final status based on CLI output.

**Outputs**

* Persistent state in Postgres.
* Slack messages:

  * Initial "Run started…"
  * Progress updates.
  * Final summary.

---

### 3.4 Backend – Execution Engine (CLI Subprocess Wrapper)

The Execution Engine is a library/module inside the backend that wraps Cline CLI subprocess calls.

**Responsibilities**

* Be the **only** code that:

  * Executes Cline CLI commands via subprocess.
  * Manages workspace directories and instance lifecycle.
  * Parses CLI output (JSON and plain text).

* Provide an internal interface like:

  ```python
  class ClineCliClient:
      async def start_run(
          repo_url, ref, prompt, 
          provider, api_key, model_id, base_url
      ) -> Dict[str, str]:
          # Returns {instance_address, task_id, workspace_path}
      
      async def stream_events(
          instance_address, workspace_path, task_id
      ) -> AsyncIterator[RunEventSchema]:
          # Yields events from CLI output
      
      async def cancel_run(
          instance_address, workspace_path, reason
      ) -> bool:
          # Cancels task via CLI
      
      async def cleanup_instance(
          instance_address, workspace_path
      ) -> None:
          # Kills instance and cleans workspace
  ```

* Manage:

  * Subprocess execution (`asyncio.create_subprocess_exec`).
  * Workspace directory creation and cleanup.
  * Instance lifecycle (create, kill).
  * Authentication configuration via `cline auth` command.
  * Output parsing (JSON from most commands, plain text from streaming).

**Non-responsibilities**

* No Slack knowledge.
* No DB writes.

It's purely "call Cline CLI commands and capture their responses."

---

### 3.5 Cline CLI

**Responsibilities**

* Manage Cline Core instances:

  * `cline instance new` - Start new instance, auto-assigns port.
  * `cline instance kill <address>` - Stop instance.

* Configure authentication:

  * `cline auth --provider ... --apikey ... --modelid ...` - Set API keys.

* Execute tasks:

  * `cline task new -y "prompt"` - Create task in YOLO/autonomous mode.
  * `cline task view --follow` - Stream output in real-time.
  * `cline task pause` - Cancel current task.

* Handle workspace management:

  * Uses current working directory as workspace.
  * Manages file operations within workspace.

**Integration Pattern**

This is the **same pattern used by GitHub Actions integration** - proven and reliable.

---

### 3.6 Cline Core

**Responsibilities**

* Execute AI agent logic:

  * File operations (read, write, edit).
  * Command execution.
  * Browser automation.
  * Code analysis and generation.

* Managed automatically by Cline CLI:

  * CLI starts/stops Cline Core as needed.
  * CLI handles gRPC communication internally.

**Execution Environment**

* Cline Core can:

  * Spawn subprocesses.
  * Use containers/devcontainers.
  * Integrate additional tools (test runner, static analyzer, etc.).

Backend doesn't interact with Cline Core directly - all communication goes through Cline CLI.

---

### 3.7 External: Git Provider

**Responsibilities**

* Host the code repos Cline operates on.
* Provide access via:

  * HTTPS (PAT/token).
  * SSH (key-based).

The Execution Engine (via `git clone`) is responsible for cloning repos to workspace directories.

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

     * "Starting Cline run for `Run unit tests and summarize failures`…"

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
     * `provider`, `api_key`, `model_id` (from config)
     * metadata (Slack IDs, etc.)

8. Execution Engine:

   * Clones repository to `/home/app/workspaces/run-TIMESTAMP/`
   * Executes: `cline instance new` (creates instance at e.g., `localhost:50052`)
   * Executes: `cline auth --provider ... --apikey ... --modelid ...` (configures authentication)
   * Executes: `cline task new -y "prompt"` (creates task in YOLO mode)
   * Returns `{instance_address, task_id, workspace_path}` to Orchestrator.

9. Orchestrator:

   * Updates `runs` row with `cline_instance_address`, `workspace_path`.
   * Transitions status to `RUNNING`.

---

### 4.4 Execution + Events

10. Execution Engine executes: `cline task view --follow --address <instance>`

11. Cline CLI:

    * Streams output line by line (stdout).
    * Shows progress: "Analyzing code...", "Running tests...", etc.
    * Exits when task completes (exit code 0 = success, non-zero = failure).

12. Execution Engine:

    * For each line of output:

      * Creates `RunEventSchema` with event type and message.
      * Yields to Orchestrator.

13. Orchestrator:

    * Updates `runs` table accordingly:

      * Status transitions.
      * Timestamps.
      * Summary.
    * Calls Slack Gateway helper functions to:

      * Post progress updates in the original thread.
      * Post a final summary when complete.

14. Cleanup:

    * Execution Engine executes: `cline instance kill <address>`
    * Deletes workspace directory: `rm -rf /home/app/workspaces/run-TIMESTAMP/`

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
* `cline_run_id` (task ID from Cline CLI)
* `cline_instance_address` (e.g., `localhost:50052`)
* `workspace_path` (e.g., `/home/app/workspaces/run-20231203-1030/`)
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

  * Exposes HTTP (e.g., `http://localhost:8000`).
  * Includes Cline CLI (installed via npm).
  * Connected to Postgres.

* `postgres`:

  * Data store for backend.

Expose backend to Slack with ngrok:

* `ngrok http 8000`
* Use the forwarded URL as Slack's Request URL.

**Note:** No separate Cline Core service needed - CLI manages instances automatically.

---

### 6.2 Cloud (MVP)

**Backend**

* Single container image (includes Cline CLI).
* Deployed to:

  * ECS, Kubernetes, or any container platform.
* Exposes:

  * HTTPS endpoint for Slack (`/slack/events`, `/slack/interactivity`).
* Connects to:

  * Managed Postgres (RDS, Cloud SQL, etc.).
* Embedded Cline CLI:

  * Manages Cline Core instances internally.
  * No external gRPC endpoints needed.

**Authentication**

* API keys configured via environment variables:

  * `CLINE_PROVIDER` (e.g., "anthropic", "openai-native")
  * `CLINE_API_KEY`
  * `CLINE_MODEL_ID`
  * `CLINE_BASE_URL` (optional, for OpenAI-compatible providers)

**See [CLINE_CLI_AUTHENTICATION.md](./CLINE_CLI_AUTHENTICATION.md) for complete authentication setup.**

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

    * "PR #123 opened – run `/cline run review` to have Cline review it."

### 7.3 Scaling Out

* If execution load becomes heavy:

  * Run multiple backend instances (horizontally scale).
  * Each instance manages its own Cline CLI instances and workspaces.
  * Shared PostgreSQL for coordination.

---

## 8. Summary

* **Single backend container** is the public face:

  * Handles Slack, orchestration, and persistence.
  * Embeds Cline CLI for execution.

* **Cline CLI** manages Cline Core automatically:

  * Clones repos to isolated workspaces.
  * Runs agent tasks autonomously (YOLO mode).
  * Streams output back to backend.

* The architecture is:

  * Simple enough for a 4-person team to ship an MVP.
  * Uses proven patterns (GitHub Actions integration).
  * Production-ready with minimal setup.
  * Structured enough to later:

    * Add dashboards.
    * Support multiple workspaces.
    * Scale horizontally.
