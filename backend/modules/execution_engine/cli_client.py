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
from typing import AsyncIterator, Dict, Optional
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
        Start a new Cline run using CLI commands.
        
        Args:
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
            # 1. Clone repository to workspace
            workspace_path = await self._clone_repository(repo_url, ref)
            logger.info(f"Cloned {repo_url} to {workspace_path}")
            
            # 2. Configure authentication FIRST (creates config file needed by instance)
            await self._configure_auth(
                workspace_path,
                provider,
                api_key,
                model_id,
                base_url
            )
            logger.info(f"Configured {provider} authentication")
            
            # 3. Create Cline instance (now config exists)
            instance_address = await self._create_instance(workspace_path)
            logger.info(f"Created Cline instance at {instance_address}")
            
            # 4. Create task with YOLO mode (autonomous)
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
        
        Args:
            instance_address: Cline instance address
            workspace_path: Workspace directory path
            task_id: Task ID
            
        Yields:
            RunEventSchema: Events from the running task
        """
        logger.info(f"Starting event stream for task {task_id}")
        
        try:
            # Use `cline task view --follow-complete` to stream until completion
            cmd = [
                "cline", "task", "view",
                "--follow-complete",
                "--output-format", "plain",
                "--address", instance_address
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_path
            )
            
            line_count = 0
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                line_text = line.decode('utf-8').strip()
                if not line_text:
                    continue
                
                line_count += 1
                
                # Create event from CLI output
                event = RunEventSchema(
                    run_id=task_id,
                    cline_run_id=task_id,
                    event_type="step",
                    timestamp=datetime.utcnow(),
                    data={"line_number": str(line_count)},
                    message=line_text
                )
                
                yield event
                
                log_run_event("cli_output", task_id, message=line_text[:100])
            
            # Wait for process to complete
            await process.wait()
            
            # Final completion event
            if process.returncode == 0:
                yield RunEventSchema(
                    run_id=task_id,
                    cline_run_id=task_id,
                    event_type="complete",
                    timestamp=datetime.utcnow(),
                    data={"exit_code": str(process.returncode)},
                    message="Task completed successfully"
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
    
    async def _clone_repository(self, repo_url: str, ref: str) -> str:
        """
        Clone repository to a temporary workspace.
        
        Args:
            repo_url: Git repository URL
            ref: Branch or commit to checkout
            
        Returns:
            str: Path to cloned workspace
        """
        # Create unique workspace directory
        workspace_name = f"run-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        workspace_path = os.path.join(self.workspace_base, workspace_name)
        
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
        
        return workspace_path
    
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
        
        Args:
            instance_address: Cline instance address
            workspace_path: Workspace directory
            prompt: Task description
            
        Returns:
            str: Task ID
        """
        cmd = [
            "cline", "task", "new",
            "-y",  # YOLO mode (autonomous)
            "--address", instance_address,
            "--output-format", "json",
            prompt
        ]
        
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
