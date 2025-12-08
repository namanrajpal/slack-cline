# Plan → Act Workflow Implementation

## Overview

Implemented a two-phase workflow where Cline first creates a plan for user approval, then executes it autonomously after approval.

## Workflow

### 1. User Initiates Task (Slack)
```
/cline run "add unit tests to utils.py"
```

### 2. Backend Creates Task in PLAN Mode
- Task starts with `status = PLANNING`
- CLI command: `cline task new -m plan "add unit tests"` (NO -y flag)
- Cline analyzes codebase and creates a detailed plan

### 3. Plan Completion Detection
When Cline finishes the plan:
- Event type: `task_response` or `complete`
- Status transitions: `PLANNING` → `AWAITING_APPROVAL`
- Backend fetches plan summary via `get_task_summary()`

### 4. User Sees Plan in Slack
Slack message with:
```
📋 Cline's Plan:

[Plan summary from get_task_summary()]

[✅ Approve & Execute] [❌ Cancel] [💬 Modify]
```

### 5. User Approves Plan
User clicks "Approve & Execute" button:
- Backend calls `orchestrator.approve_run(run_id)`
- Orchestrator calls `cli_client.approve_plan(instance, workspace)`
- CLI command: `cline task send -y -m act --approve "Proceed with the plan"`
- Status transitions: `AWAITING_APPROVAL` → `RUNNING`

### 6. Cline Executes Autonomously
- Switches to ACT mode with YOLO enabled
- Executes plan without further approval required
- Posts final results to Slack

## Implementation Status

### ✅ Completed

1. **cli_client.py**
   - Updated `_create_task()` to start in PLAN mode (removed -y, added -m plan)
   - Added `approve_plan()` method
   - Added `get_task_summary()` for fetching final response

2. **models/run.py**
   - Added `PLANNING` status
   - Added `AWAITING_APPROVAL` status

3. **orchestrator/service.py**
   - Updated `start_run()` to use `PLANNING` status

### 🚧 TODO

1. **orchestrator/service.py**
   - Update `_process_run_event()` to detect plan completion
   - Change status from `PLANNING` to `AWAITING_APPROVAL`
   - Post plan to Slack with approval buttons
   - Add `approve_run()` method

2. **slack_gateway/handlers.py**
   - Add handler for "Approve" button click
   - Add handler for "Cancel" button click
   - Add handler for "Modify" button click (opens chat)

3. **utils/slack_client.py**
   - Add `create_plan_approval_blocks()` method
   - Include interactive buttons

4. **schemas/slack.py**
   - Add `ApproveRunCommand` schema

5. **Database Migration**
   - Add migration for new `PLANNING` and `AWAITING_APPROVAL` enum values

## Code Snippets

### Detect Plan Completion (_process_run_event)

```python
# In _process_run_event(), after fetching run from database:

# Detect plan completion
if run.status == RunStatus.PLANNING and event.event_type == "task_response":
    # Plan is complete, fetch summary
    plan_summary = await self.cli_client.get_task_summary(
        run.cline_instance_address,
        run.workspace_path
    )
    
    # Update status to awaiting approval
    run.status = RunStatus.AWAITING_APPROVAL
    run.summary = plan_summary
    await session.commit()
    
    # Post plan to Slack with approval buttons
    await self._post_plan_approval_message(run, plan_summary)
    return  # Don't mark as complete yet
```

### approve_run() Method

```python
async def approve_run(self, run_id: str, session: AsyncSession) -> bool:
    """
    Approve a plan and start execution.
    
    Args:
        run_id: Run ID to approve
        session: Database session
        
    Returns:
        bool: True if approval was successful
    """
    result = await session.execute(
        select(RunModel).where(RunModel.id == UUID(run_id))
    )
    run = result.scalar_one_or_none()
    
    if not run or run.status != RunStatus.AWAITING_APPROVAL:
        return False
    
    metadata = self._run_metadata.get(run_id)
    if not metadata:
        return False
    
    # Approve via CLI (switches to ACT mode + YOLO)
    success = await self.cli_client.approve_plan(
        metadata["instance_address"],
        metadata["workspace_path"],
        "Proceed with the plan"
    )
    
    if success:
        run.status = RunStatus.RUNNING
        await session.commit()
        log_run_event("plan_approved", run_id)
    
    return success
```

### Slack Approval Blocks

```python
def create_plan_approval_blocks(
    self,
    task_prompt: str,
    plan_summary: str,
    run_id: str
) -> list:
    """Create Slack blocks for plan approval."""
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📋 Cline's Plan"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Task:* {task_prompt}"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"```\n{plan_summary[:2000]}\n```"}
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ Approve & Execute"},
                    "style": "primary",
                    "value": run_id,
                    "action_id": "approve_plan"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ Cancel"},
                    "style": "danger",
                    "value": run_id,
                    "action_id": "cancel_run"
                }
            ]
        }
    ]
```

## Testing

### Test Plan Workflow

```powershell
# 1. Restart backend
docker-compose restart backend

# 2. Create run from Admin Panel or Slack
/cline run "create a README file"

# 3. Verify status transitions in logs:
# - PLANNING (initial)
# - AWAITING_APPROVAL (after plan complete)
# - RUNNING (after approval)
# - SUCCEEDED (after execution)

# 4. Check Slack for:
# - Initial "Creating plan..." message
# - Plan summary with approval buttons
# - Final execution results
```

## Benefits

✅ **User Control**: See plan before execution  
✅ **Safety**: No surprise changes without approval  
✅ **Transparency**: Understand what Cline will do  
✅ **Flexibility**: Can modify plan before execution  
✅ **Audit Trail**: All approvals logged in database

## Future Enhancements

- **Modify Plan**: Allow user to send feedback before approval
- **Multiple Approvers**: Require approval from specific users
- **Auto-Approval**: Configure channels/users that auto-approve
- **Plan Diff**: Show what files will be changed
- **Cost Estimation**: Estimate API costs before execution
