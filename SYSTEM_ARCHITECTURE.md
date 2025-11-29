# System Architecture – Cline × Slack Runner

## 1. High-level View

We split the system into three main components:

1. **Slack App (Interface Layer)**
2. **Backend / Orchestrator (Brain)**
3. **Runner / Cline Service (Execution)**

Plus integrations:

- **Git providers** (GitHub/GitLab/etc.)
- **Postgres** (Backend state)
- **Object storage** (logs, artifacts – optional in MVP)

### 1.1 Architecture Diagram

```mermaid
flowchart LR
  subgraph Slack["Slack Workspace"]
    U[Developer] -->|/cline run <task>| SA[Slack App / Bot]
  end

  subgraph Backend["Backend / Orchestrator"]
    SA -->|Events API / Interactivity| SB[Backend API]
    SB -->|REST / SSE| CR[Cline Runner API]
    SB -->|read/write| DB[(Postgres)]
  end

  subgraph Runner["Runner / Execution Plane"]
    CR -->|create run| EC[Execution Controller]
    EC -->|clone repo + run task| CT[(Worker Env)]
    CT <-->|tools, file ops| CCORE[Cline Core / Agent]
  end

  GH[Git Provider] -->|clone over HTTPS/SSH| CT
  SB -->|status updates| SA
