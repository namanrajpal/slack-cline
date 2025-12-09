"""
Execution Engine using Cline CLI subprocess calls.

This module provides a high-level interface for starting runs, streaming events,
and managing Cline executions using the Cline CLI commands (subprocess calls).

This approach is simpler and more reliable than direct gRPC integration:
- No proto compilation needed
- Cline CLI handles instance and workspace management
- Proven pattern from GitHub Actions integration
"""

import asyncio
import json
import os
import subprocess
import tempfile
from typing import AsyncIterator, Dict, Literal, Optional
from datetime import datetime
from pathlib import Path

from schemas.run import RunEventSchema
from utils.logging import get_logger, log_run_event

logger = get_logger("execution.cli")


class ClineCliClient:
    """
    Client for executing Cline tasks using the Cline CLI.
    
    This uses subprocess calls to the `cline` command, similar to how
    GitHub Actions integration works.
    """
    
    def __init__(self, workspace_base: str = None):
        """
        Initialize the CLI client.
        
        Args:
            workspace_base: Base directory for cloning repositories
        """
        self.workspace_base = workspace_base or "/home/app/workspaces"
        Path(self.workspace_base).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized Cline CLI client with workspace base: {self.workspace_base}")
    
    async def start_run(
        self,
        workspace_path: str,
        repo_url: str,
        ref_type: str,
        ref: str,
        prompt: str,
        provider: str,
        api_key: str,
        model_id: str,
        base_url: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Start a new Cline run using CLI commands in an existing workspace.
        
        The workspace should already exist and be up-to-date (use ensure_workspace first).
        
        Args:
            workspace_path: Existing workspace directory path
            repo_url: Git repository URL
            ref_type: Reference type ("branch" or "commit")
            ref: Branch name or commit hash
            prompt: Task description
            provider: LLM provider ID (e.g., "anthropic", "openai-native", "openrouter")
            api_key: API key for the provider
            model_id: Model ID to use (e.g., "claude-sonnet-4-5-20250929")
            base_url: Optional base URL for OpenAI-compatible providers
            metadata: Additional metadata
            
        Returns:
            dict: Contains instance_address, task_id, workspace_path
            
        Raises:
            RuntimeError: If run fails to start
        """
        start_time = datetime.utcnow()
        
        try:
            # Workspace should already be ready (cloned/updated by ensure_workspace)
            logger.info(f"Using existing workspace at {workspace_path}")
            
            # 2. Install dependencies (auto-detect project type)
            # await self._setup_workspace(workspace_path)
            # logger.info(f"Installed dependencies in {workspace_path}")
            
            # 3. Configure authentication FIRST (creates config file needed by instance)
            await self._configure_auth(
                workspace_path,
                provider,
                api_key,
                model_id,
                base_url
            )
            logger.info(f"Configured {provider} authentication")
            
            # 4. Create Cline instance (now config exists)
            instance_address = await self._create_instance(workspace_path)
            logger.info(f"Created Cline instance at {instance_address}")
            
            # 5. Create task with YOLO mode (autonomous)
            task_id = await self._create_task(instance_address, workspace_path, prompt)
            logger.info(f"Created task {task_id} on instance {instance_address}")
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_run_event(
                "cli_run_started",
                task_id,
                instance=instance_address,
                workspace=workspace_path,
                duration=duration
            )
            
            return {
                "instance_address": instance_address,
                "task_id": task_id,
                "workspace_path": workspace_path
            }
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_run_event("cli_run_failed", "unknown", error=str(e), duration=duration)
            logger.error(f"Failed to start run: {e}")
            raise RuntimeError(f"Failed to start Cline run: {e}")
    
    async def stream_events(
        self, 
        instance_address: str, 
        workspace_path: str,
        task_id: str
    ) -> AsyncIterator[RunEventSchema]:
        """
        Stream events from a Cline task using CLI output.
        
        In PLAN mode, implements timeout-based detection of plan completion since
        Cline waits indefinitely for user input after presenting the plan.
        
        Args:
            instance_address: Cline instance address
            workspace_path: Workspace directory path
            task_id: Task ID
            
        Yields:
            RunEventSchema: Events from the running task
        """
        logger.info(f"Starting event stream for task {task_id}")
        
        # Timeout configuration for PLAN mode idle detection
        PLAN_IDLE_TIMEOUT = 30.0  # seconds - if no events for this long, assume plan is complete
        MAX_TIMEOUT_RETRIES = 2  # Maximum number of times to retry after timeout
        timeout_count = 0
        
        try:
            # Use `cline task view --follow` (not --follow-complete) for better control
            cmd = [
                "cline", "task", "view",
                "--follow",  # Follow forever (we'll timeout ourselves)
                "--output-format", "plain",
                "--address", instance_address
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # Merge stderr into stdout
                cwd=workspace_path
            )
            
            line_count = 0
            last_event_time = asyncio.get_event_loop().time()
            
            while True:
                try:
                    # Read with timeout to detect idle state
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=PLAN_IDLE_TIMEOUT
                    )
                    
                    if not line:
                        # EOF - process exited
                        break
                    
                    line_text = line.decode('utf-8').strip()
                    if not line_text:
                        continue
                    
                    line_count += 1
                    last_event_time = asyncio.get_event_loop().time()
                    
                    # Detect event type
                    event_type = "step"
                    
                    # Check for task completion markers
                    if "### Task completed" in line_text:
                        event_type = "task_response"
                    elif "### Progress" in line_text:
                        event_type = "progress"
                    
                    # Check for approval request patterns
                    approval_patterns = [
                        "wants to execute",
                        "Approve?",
                        "approve this action",
                        "waiting for approval",
                        "Do you want to proceed",
                        "wants to run",
                        "wants to write",
                        "wants to read",
                        "Allow this action",
                        "### Tool use request",
                        "execute_command:",
                        "write_to_file:",
                        "read_file:",
                    ]
                    
                    for pattern in approval_patterns:
                        if pattern.lower() in line_text.lower():
                            event_type = "approval_required"
                            break
                    
                    # Create event from CLI output
                    event = RunEventSchema(
                        run_id=task_id,
                        cline_run_id=task_id,
                        event_type=event_type,
                        timestamp=datetime.utcnow(),
                        data={
                            "line_number": str(line_count),
                            "requires_approval": event_type == "approval_required"
                        },
                        message=line_text
                    )
                    
                    yield event
                    log_run_event("cli_output", task_id, message=line_text[:100])
                    
                except asyncio.TimeoutError:
                    # No events for PLAN_IDLE_TIMEOUT seconds
                    # Cline is likely waiting for input (plan complete)
                    timeout_count += 1
                    logger.info(f"Idle timeout reached ({PLAN_IDLE_TIMEOUT}s, attempt {timeout_count}/{MAX_TIMEOUT_RETRIES}), checking if plan is complete...")
                    
                    # Fetch the current state to get the plan (request full output for plans)
                    plan_summary = await self.get_task_summary(instance_address, workspace_path, full_output=True)
                    
                    # Enhanced plan detection heuristics
                    is_complete_plan = self._is_complete_plan(plan_summary, line_count)
                    
                    if is_complete_plan:
                        logger.info(f"Plan detected ({len(plan_summary)} chars, {line_count} lines), posting for approval")
                        
                        yield RunEventSchema(
                            run_id=task_id,
                            cline_run_id=task_id,
                            event_type="plan_complete",
                            timestamp=datetime.utcnow(),
                            data={
                                "idle_timeout": str(PLAN_IDLE_TIMEOUT),
                                "plan_length": str(len(plan_summary)),
                                "line_count": str(line_count)
                            },
                            message=plan_summary
                        )
                        
                        # Stop streaming - plan is ready for approval
                        process.kill()
                        await process.wait()
                        return
                    elif timeout_count >= MAX_TIMEOUT_RETRIES:
                        # Exceeded max retries - assume plan is complete even if not detected
                        logger.warning(f"Max timeout retries ({MAX_TIMEOUT_RETRIES}) reached, assuming plan is complete")
                        
                        yield RunEventSchema(
                            run_id=task_id,
                            cline_run_id=task_id,
                            event_type="plan_complete",
                            timestamp=datetime.utcnow(),
                            data={
                                "idle_timeout": str(PLAN_IDLE_TIMEOUT),
                                "plan_length": str(len(plan_summary)),
                                "line_count": str(line_count),
                                "forced_after_retries": "true"
                            },
                            message=plan_summary or "Plan detection timed out - please review task output"
                        )
                        
                        # Stop streaming
                        process.kill()
                        await process.wait()
                        return
                    else:
                        # Probably just processing or slow - keep waiting
                        logger.info(f"Timeout but plan not complete yet (still processing), continuing... ({timeout_count}/{MAX_TIMEOUT_RETRIES})")
                        continue
            
            # Process exited naturally
            await process.wait()
            
            # Fetch final summary
            final_summary = "Task completed successfully"
            if process.returncode == 0:
                logger.info("Fetching final task summary...")
                final_summary = await self.get_task_summary(instance_address, workspace_path)
                logger.info(f"Task summary captured ({len(final_summary)} chars)")
            
            # Final completion event
            if process.returncode == 0:
                yield RunEventSchema(
                    run_id=task_id,
                    cline_run_id=task_id,
                    event_type="complete",
                    timestamp=datetime.utcnow(),
                    data={
                        "exit_code": str(process.returncode),
                        "has_summary": str(len(final_summary) > 50)
                    },
                    message=final_summary
                )
            else:
                yield RunEventSchema(
                    run_id=task_id,
                    cline_run_id=task_id,
                    event_type="error",
                    timestamp=datetime.utcnow(),
                    data={"exit_code": str(process.returncode)},
                    message=f"Task failed with exit code {process.returncode}"
                )
                
        except Exception as e:
            logger.error(f"Error streaming events for task {task_id}: {e}")
            raise
    
    def _is_complete_plan(self, plan_summary: str, line_count: int) -> bool:
        """
        Determine if the fetched plan summary represents a complete plan.
        
        Uses multiple heuristics to avoid false positives during active planning:
        - Minimum content length (avoid detecting during initial exploration)
        - Look for plan-specific markers (structured content, sections)
        - Check for "still working" indicators (checkpoints, API calls)
        
        Args:
            plan_summary: The plan text fetched from task view
            line_count: Number of lines processed so far
            
        Returns:
            bool: True if this appears to be a complete plan ready for approval
        """
        if not plan_summary:
            return False
        
        # Require substantial content (avoid early detection during file reading)
        if len(plan_summary) < 500:
            logger.debug(f"Plan too short ({len(plan_summary)} chars), waiting for more content")
            return False
        
        # Check for "still working" indicators (checkpoint messages, API calls in progress)
        still_working_patterns = [
            "Checkpoint created",
            "API request",
            "↑", "↓", "←", "→",  # Token usage indicators in progress
            "Reading file",
            "Searching",
            "Analyzing",
        ]
        
        for pattern in still_working_patterns:
            if pattern in plan_summary:
                logger.debug(f"Found 'still working' pattern: {pattern}")
                return False
        
        # Look for plan completion indicators with more flexible matching
        plan_complete_markers = {
            "section_header": ["## ", "### "],  # Strong indicator - section/subsection headers
            "plan_intro": ["Here's", "This approach", "My plan"],  # Plan introduction phrases
            "numbered_list": ["1.", "2.", "3."],  # Multiple numbered items
            "plan_keywords": ["### Progress", "Steps:", "I'll proceed", "I will"],
        }
        
        # Count different types of markers
        has_section_header = any(marker in plan_summary for marker in plan_complete_markers["section_header"])
        has_plan_intro = any(marker in plan_summary for marker in plan_complete_markers["plan_intro"])
        numbered_items = sum(1 for marker in plan_complete_markers["numbered_list"] if marker in plan_summary)
        has_keywords = any(marker in plan_summary for marker in plan_complete_markers["plan_keywords"])
        
        # Flexible detection: consider complete if we have strong indicators
        # Strong signal: section headers + numbered list (2+ items)
        if has_section_header and numbered_items >= 2:
            logger.debug(f"Plan complete: section headers + {numbered_items} numbered items")
            return True
        
        # Alternative: plan intro + numbered list
        if has_plan_intro and numbered_items >= 2:
            logger.debug(f"Plan complete: plan intro + {numbered_items} numbered items")
            return True
        
        # Fallback: multiple strong indicators
        total_indicators = sum([has_section_header, has_plan_intro, (numbered_items >= 2), has_keywords])
        if total_indicators >= 2:
            logger.debug(f"Plan complete: {total_indicators} strong indicators found")
            return True
        
        logger.debug(f"Plan not complete: section_header={has_section_header}, plan_intro={has_plan_intro}, numbered_items={numbered_items}, keywords={has_keywords}")
        return False
    
    async def get_task_summary(
        self,
        instance_address: str,
        workspace_path: str,
        full_output: bool = False
    ) -> str:
        """
        Fetch the task summary or full output.
        
        The `cline task view --follow-complete` command exits BEFORE outputting
        the "### Task completed" section. This method calls `cline task view`
        (without --follow) to get the complete output including the final response.
        
        Args:
            instance_address: Cline instance address
            workspace_path: Workspace directory
            full_output: If True, return full task output; if False, extract "Task completed" section
            
        Returns:
            str: The task summary/response, or a default message if not available
        """
        cmd = [
            "cline", "task", "view",
            "--output-format", "plain",
            "--address", instance_address
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_path
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.warning(f"Failed to get task summary (exit {process.returncode})")
                return "Task completed successfully"
            
            output = stdout.decode('utf-8') if stdout else ""
            
            # If full_output requested, return everything
            if full_output:
                logger.info(f"Returning full task output ({len(output)} chars)")
                return output.strip()
            
            # Parse the "### Task completed" section from output
            # This section contains Cline's final response to the user
            summary_lines = []
            in_task_completed = False
            
            for line in output.split('\n'):
                stripped = line.strip()
                
                # Start capturing at "### Task completed"
                if "### Task completed" in stripped:
                    in_task_completed = True
                    # Don't include the "### Task completed" header itself
                    continue
                
                # Stop at "### Progress" (if it comes after Task completed)
                if "### Progress" in stripped and in_task_completed:
                    break
                
                # Capture content in the task completed section
                if in_task_completed and stripped:
                    summary_lines.append(stripped)
            
            if summary_lines:
                summary = "\n".join(summary_lines)
                logger.info(f"Extracted task summary ({len(summary_lines)} lines)")
                return summary
            else:
                # Fallback: return last portion of output if no "### Task completed" found
                lines = [l.strip() for l in output.split('\n') if l.strip()]
                if len(lines) > 10:
                    # Get last 20 lines as summary
                    return "\n".join(lines[-20:])
                elif lines:
                    return "\n".join(lines)
                else:
                    return "Task completed successfully"
                    
        except Exception as e:
            logger.error(f"Error getting task summary: {e}")
            return "Task completed successfully"

    async def cancel_run(
        self, 
        instance_address: str,
        workspace_path: str,
        reason: str = "User requested"
    ) -> bool:
        """
        Cancel a running Cline task.
        
        Args:
            instance_address: Cline instance address
            workspace_path: Workspace directory
            reason: Cancellation reason
            
        Returns:
            bool: True if cancellation was successful
        """
        try:
            # Use `cline task pause` to cancel the current task
            cmd = ["cline", "task", "pause", "--address", instance_address]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_path
            )
            
            await process.wait()
            success = process.returncode == 0
            
            if success:
                logger.info(f"Cancelled task on instance {instance_address}: {reason}")
            else:
                logger.warning(f"Failed to cancel task on instance {instance_address}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error cancelling task: {e}")
            return False
    
    async def cleanup_instance(
        self,
        instance_address: str,
        workspace_path: str = None
    ) -> None:
        """
        Clean up a Cline instance and its workspace.
        
        Args:
            instance_address: Instance to kill
            workspace_path: Workspace to clean up (optional)
        """
        try:
            # Kill the instance
            cmd = ["cline", "instance", "kill", instance_address]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            logger.info(f"Killed instance {instance_address}")
            
            # Clean up workspace if provided
            if workspace_path and os.path.exists(workspace_path):
                import shutil
                shutil.rmtree(workspace_path, ignore_errors=True)
                logger.info(f"Cleaned up workspace {workspace_path}")
                
        except Exception as e:
            logger.error(f"Error cleaning up instance: {e}")
    
    async def _configure_auth(
        self,
        workspace_path: str,
        provider: str,
        api_key: str,
        model_id: str,
        base_url: Optional[str] = None
    ) -> None:
        """
        Configure authentication using CLI auth command.
        
        This must be called BEFORE creating an instance, as the instance
        requires the config file created by this command.
        
        Args:
            workspace_path: Workspace directory
            provider: Provider ID (e.g., "anthropic", "openai-native", "openrouter")
            api_key: API key for the provider
            model_id: Model ID to use (e.g., "claude-sonnet-4-5-20250929")
            base_url: Optional base URL for OpenAI-compatible providers
            
        Raises:
            RuntimeError: If authentication configuration fails
        """
        cmd = [
            "cline", "auth",
            "--provider", provider,
            "--apikey", api_key,
            "--modelid", model_id,
            "--output-format", "json"
        ]
        
        # Add base URL for OpenAI-compatible providers
        if base_url:
            cmd.extend(["--baseurl", base_url])
        
        logger.info(f"Running auth command: cline auth --provider {provider} --modelid {model_id}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,  # Prevent stdin blocking
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workspace_path
        )
        
        stdout, stderr = await process.communicate()
        
        # Log full CLI output for debugging
        stdout_text = stdout.decode('utf-8') if stdout else ""
        stderr_text = stderr.decode('utf-8') if stderr else ""
        
        logger.info(f"CLI auth command completed (exit code: {process.returncode})")
        if stdout_text:
            logger.info(f"CLI auth stdout:\n{stdout_text}")
        if stderr_text:
            logger.warning(f"CLI auth stderr:\n{stderr_text}")
        
        if process.returncode != 0:
            raise RuntimeError(f"Failed to configure authentication (exit {process.returncode}): {stderr_text or 'Unknown error'}")
        
        logger.info("Authentication configured successfully")
    
    async def approve_plan(
        self,
        instance_address: str,
        workspace_path: str,
        message: str = "Proceed with the plan"
    ) -> bool:
        """
        Approve Cline's plan and switch from PLAN mode to ACT mode with autonomous execution.
        
        This sends approval to proceed with the plan, switches to ACT mode,
        and enables YOLO (autonomous) mode so Cline executes without further approval.
        
        Args:
            instance_address: Cline instance address
            workspace_path: Workspace directory
            message: Message to send with approval (default: "Proceed with the plan")
            
        Returns:
            bool: True if approval was sent successfully
        """
        cmd = [
            "cline", "task", "send",
            "-y",  # Enable YOLO/autonomous mode
            "-m", "act",  # Switch to ACT mode
            "--approve",  # Approve the plan
            "--address", instance_address,
            message
        ]
        
        logger.info(f"Approving plan and switching to ACT mode (YOLO) for instance {instance_address}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_path
            )
            
            stdout, stderr = await process.communicate()
            
            stdout_text = stdout.decode('utf-8') if stdout else ""
            stderr_text = stderr.decode('utf-8') if stderr else ""
            
            if process.returncode == 0:
                logger.info("Plan approved, switched to autonomous ACT mode")
                return True
            else:
                logger.error(f"Failed to approve plan: {stderr_text}")
                return False
                
        except Exception as e:
            logger.error(f"Error approving plan: {e}")
            return False

    async def send_message(
        self,
        instance_address: str,
        workspace_path: str,
        message: str
    ) -> bool:
        """
        Send a message to a running Cline task to continue the conversation.
        
        This is used for interactive conversations where the user provides
        additional input, clarifications, or answers to Cline's questions.
        
        Args:
            instance_address: Cline instance address
            workspace_path: Workspace directory
            message: Message text from the user
            
        Returns:
            bool: True if message was sent successfully
        """
        cmd = [
            "cline", "task", "send",
            "--address", instance_address,
            message
        ]
        
        logger.info(f"Sending user message to instance {instance_address}: {message[:100]}...")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_path
            )
            
            stdout, stderr = await process.communicate()
            
            stdout_text = stdout.decode('utf-8') if stdout else ""
            stderr_text = stderr.decode('utf-8') if stderr else ""
            
            if process.returncode == 0:
                logger.info("User message sent successfully")
                return True
            else:
                logger.error(f"Failed to send message: {stderr_text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    async def send_response(
        self,
        instance_address: str,
        workspace_path: str,
        action: Literal["approve", "deny"],
        message: Optional[str] = None
    ) -> bool:
        """
        Send an approval or denial response to a running Cline task.
        
        Use this when Cline is waiting for user approval to execute a command
        or perform an action (during execution, not for approving the initial plan).
        
        For approving the initial plan and switching to ACT mode, use approve_plan() instead.
        
        Args:
            instance_address: Cline instance address
            workspace_path: Workspace directory
            action: "approve" or "deny"
            message: Optional message to send with the response
            
        Returns:
            bool: True if response was sent successfully
        """
        cmd = ["cline", "task", "send", "--address", instance_address]
        
        if action == "approve":
            cmd.append("--approve")
        elif action == "deny":
            cmd.append("--deny")
        
        if message:
            cmd.append(message)
        
        logger.info(f"Sending {action} response to instance {instance_address}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_path
            )
            
            stdout, stderr = await process.communicate()
            
            stdout_text = stdout.decode('utf-8') if stdout else ""
            stderr_text = stderr.decode('utf-8') if stderr else ""
            
            if process.returncode == 0:
                logger.info(f"Response sent successfully: {action}")
                return True
            else:
                logger.error(f"Failed to send response: {stderr_text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending response: {e}")
            return False

    async def ensure_workspace(
        self,
        workspace_path: str,
        repo_url: str,
        ref: str
    ) -> str:
        """
        Ensure workspace exists and is up-to-date.
        
        If workspace doesn't exist, clones the repository.
        If workspace exists, pulls latest changes.
        
        Args:
            workspace_path: Target workspace directory path
            repo_url: Git repository URL
            ref: Branch or commit to checkout
            
        Returns:
            str: Path to workspace
        """
        if os.path.exists(workspace_path):
            # Workspace exists - update it
            logger.info(f"Workspace exists at {workspace_path}, updating...")
            await self._update_workspace(workspace_path, ref)
        else:
            # First time - clone it
            logger.info(f"Workspace doesn't exist, cloning to {workspace_path}...")
            await self._clone_workspace(repo_url, ref, workspace_path)
        
        return workspace_path
    
    async def _update_workspace(self, workspace_path: str, ref: str):
        """
        Update existing workspace with latest changes.
        
        Args:
            workspace_path: Workspace directory path
            ref: Branch to checkout and pull
        """
        try:
            # Reset any local changes
            await self._run_git_command(workspace_path, ["reset", "--hard"])
            logger.info("Reset local changes")
            
            # Clean untracked files
            await self._run_git_command(workspace_path, ["clean", "-fd"])
            logger.info("Cleaned untracked files")
            
            # Checkout correct branch
            await self._run_git_command(workspace_path, ["checkout", ref])
            logger.info(f"Checked out branch: {ref}")
            
            # Pull latest changes
            await self._run_git_command(workspace_path, ["pull", "origin", ref])
            logger.info("Pulled latest changes")
            
        except Exception as e:
            logger.error(f"Error updating workspace: {e}")
            raise RuntimeError(f"Failed to update workspace: {e}")
    
    async def _clone_workspace(self, repo_url: str, ref: str, workspace_path: str):
        """
        Clone repository to workspace (first time only).
        
        Args:
            repo_url: Git repository URL
            ref: Branch to checkout
            workspace_path: Target directory path
        """
        # Create parent directory if needed
        os.makedirs(os.path.dirname(workspace_path), exist_ok=True)
        
        # Clone repository
        cmd = ["git", "clone", "--depth", "1", "--branch", ref, repo_url, workspace_path]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
            raise RuntimeError(f"Failed to clone repository: {error_msg}")
        
        logger.info(f"Cloned repository to {workspace_path}")
    
    async def configure_git_identity(
        self,
        workspace_path: str,
        user_name: str,
        user_email: str
    ) -> None:
        """
        Configure git identity in workspace for commit attribution.
        
        This sets the git user.name and user.email for the workspace so that
        any commits made by Cline are attributed to the actual user.
        
        Args:
            workspace_path: Workspace directory
            user_name: User's full name (e.g., "Alice Smith")
            user_email: User's email (e.g., "alice@company.com")
        """
        try:
            # Set git user.name
            await self._run_git_command(
                workspace_path,
                ["config", "user.name", user_name]
            )
            logger.info(f"Set git user.name: {user_name}")
            
            # Set git user.email
            await self._run_git_command(
                workspace_path,
                ["config", "user.email", user_email]
            )
            logger.info(f"Set git user.email: {user_email}")
            
        except Exception as e:
            logger.error(f"Failed to configure git identity: {e}")
            raise RuntimeError(f"Failed to configure git identity: {e}")
    
    async def _run_git_command(self, workspace_path: str, args: list):
        """
        Helper to run git commands in workspace.
        
        Args:
            workspace_path: Workspace directory
            args: Git command arguments (e.g., ["pull", "origin", "main"])
        """
        cmd = ["git"] + args
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workspace_path
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
            raise RuntimeError(f"Git command failed ({' '.join(args)}): {error_msg}")
    
    async def _create_instance(self, workspace_path: str) -> str:
        """
        Create a new Cline instance in the workspace.
        
        The `cline instance new` command runs in foreground mode, keeping the
        process alive while the instance is running. We need to read output
        incrementally and return as soon as we find the instance address.
        
        Args:
            workspace_path: Directory where Cline will run
            
        Returns:
            str: Instance address (e.g., "127.0.0.1:50052")
        """
        cmd = ["cline", "instance", "new"]
        
        logger.info(f"Creating Cline instance in {workspace_path}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,  # Prevent stdin blocking
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workspace_path
        )
        
        # Read output line by line - don't wait for process to complete
        # The process runs in foreground mode and won't exit while instance is alive
        instance_address = None
        output_lines = []
        
        try:
            # Read with timeout to avoid hanging forever
            while True:
                try:
                    line_bytes = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=30.0  # 30 second timeout per line
                    )
                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for cline instance output")
                    break
                
                if not line_bytes:
                    # EOF reached
                    break
                
                line = line_bytes.decode('utf-8').strip()
                output_lines.append(line)
                logger.info(f"CLI instance new output: {line}")
                
                # Look for "Address: X.X.X.X:PORT" pattern
                if line.startswith('Address:'):
                    instance_address = line.split(':', 1)[1].strip()
                    logger.info(f"Parsed instance address: {instance_address}")
                    break
                
                # Also check for address in format "Address: 127.0.0.1:PORT"
                if 'Address:' in line:
                    parts = line.split('Address:')
                    if len(parts) > 1:
                        instance_address = parts[1].strip()
                        logger.info(f"Parsed instance address (alt): {instance_address}")
                        break
        
        except Exception as e:
            logger.error(f"Error reading instance output: {e}")
        
        # Log collected output
        full_output = '\n'.join(output_lines)
        logger.info(f"CLI instance new collected output:\n{full_output}")
        
        if instance_address:
            logger.info(f"Successfully created instance at {instance_address}")
            # Note: We don't terminate the process - it manages the instance lifecycle
            # The instance will be cleaned up when we call cleanup_instance()
            return instance_address
        
        # If we didn't find the address, check if process exited with error
        if process.returncode is not None and process.returncode != 0:
            stderr_bytes = await process.stderr.read()
            stderr_text = stderr_bytes.decode('utf-8') if stderr_bytes else ""
            raise RuntimeError(f"Failed to create instance (exit {process.returncode}): {stderr_text or 'Unknown error'}")
        
        # Fallback: try JSON parsing if output looks like JSON
        try:
            result = json.loads(full_output)
            instance_address = (
                result.get('address') or 
                result.get('instance_address') or 
                result.get('instance')
            )
            if instance_address:
                return instance_address
        except json.JSONDecodeError:
            pass
        
        raise RuntimeError(f"Failed to parse instance address from output: {full_output[:500]}")
    
    async def _create_task(
        self, 
        instance_address: str,
        workspace_path: str,
        prompt: str
    ) -> str:
        """
        Create a new task on the specified instance.
        
        Starts in PLAN mode to allow user review before execution.
        User must approve the plan via approve_plan() to switch to ACT mode.
        
        Args:
            instance_address: Cline instance address
            workspace_path: Workspace directory
            prompt: Task description
            
        Returns:
            str: Task ID
        """
        cmd = [
            "cline", "task", "new",
            "-m", "plan",  # Start in PLAN mode - Cline creates a plan first
            "--address", instance_address,
            prompt
        ]
        # NO -y flag - user must approve the plan before execution
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,  # Prevent stdin blocking
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workspace_path
        )
        
        stdout, stderr = await process.communicate()
        
        # Log full CLI output for debugging
        stdout_text = stdout.decode('utf-8') if stdout else ""
        stderr_text = stderr.decode('utf-8') if stderr else ""
        
        logger.info(f"CLI task new command completed (exit code: {process.returncode})")
        if stdout_text:
            logger.info(f"CLI task new stdout:\n{stdout_text}")
        if stderr_text:
            logger.warning(f"CLI task new stderr:\n{stderr_text}")
        
        if process.returncode != 0:
            raise RuntimeError(f"Failed to create task (exit {process.returncode}): {stderr_text or 'Unknown error'}")
        
        # Parse JSON output to get task ID
        try:
            output = json.loads(stdout_text)
            task_id = output.get('task_id', 'unknown')
            logger.info(f"Parsed task ID: {task_id}")
        except json.JSONDecodeError:
            # Fallback: use instance address as task identifier
            task_id = instance_address
            logger.warning(f"Could not parse task ID from JSON, using instance address: {task_id}")
        
        return task_id


# Global client instance
_cli_client: Optional[ClineCliClient] = None


def get_cli_client() -> ClineCliClient:
    """
    Get or create the global CLI client instance.
    
    Returns:
        ClineCliClient: Client instance
    """
    global _cli_client
    if _cli_client is None:
        _cli_client = ClineCliClient()
    return _cli_client


async def cleanup_cli_client():
    """Clean up the global CLI client."""
    global _cli_client
    if _cli_client:
        # CLI instances are managed externally
        _cli_client = None
