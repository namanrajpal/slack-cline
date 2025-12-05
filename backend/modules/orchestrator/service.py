"""
Run Orchestrator service for managing Cline run lifecycle.

This module coordinates between the Slack Gateway, Execution Engine, and database
to manage the complete lifecycle of Cline runs from creation to completion.
"""

import asyncio
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from database import get_session
from models.project import ProjectModel
from models.run import RunModel, RunStatus
from modules.execution_engine.cli_client import get_cli_client
from schemas.slack import StartRunCommand, CancelRunCommand
from schemas.run import RunEventSchema
from utils.logging import get_logger, log_run_event
from utils.slack_client import get_slack_client

logger = get_logger("orchestrator")


class RunOrchestratorService:
    """
    Service for orchestrating Cline run lifecycle.
    
    This service handles the complete lifecycle of runs from initial Slack commands
    through execution completion, coordinating between all system components.
    """
    
    def __init__(self):
        self.cli_client = get_cli_client()
        self.slack_client = get_slack_client()
        self._active_streams: Dict[str, asyncio.Task] = {}
        self._run_metadata: Dict[str, Dict] = {}  # Store instance/workspace info per run
    
    async def start_run(self, command: StartRunCommand, session: AsyncSession) -> RunModel:
        """
        Start a new Cline run from a Slack command.
        
        Args:
            command: Start run command from Slack Gateway
            session: Database session
            
        Returns:
            RunModel: Created run instance
            
        Raises:
            ValueError: If project mapping is not found
            RuntimeError: If run fails to start
        """
        log_run_event(
            "start_requested",
            run_id="pending",
            channel_id=command.channel_id,
            task_prompt=command.task_prompt[:100]
        )
        
        # Resolve project (channel -> repo mapping)
        project = await self._resolve_project(
            session, 
            command.tenant_id, 
            command.channel_id
        )
        
        if not project:
            raise ValueError(f"No repository configured for channel {command.channel_id}")
        
        # Create run in database
        run = RunModel(
            tenant_id=command.tenant_id,
            project_id=project.id,
            task_prompt=command.task_prompt,
            slack_channel_id=command.channel_id,
            status=RunStatus.QUEUED
        )
        
        session.add(run)
        await session.commit()
        await session.refresh(run)
        
        log_run_event("run_created", str(run.id), task_prompt=command.task_prompt[:100])
        
        try:
            # Start execution via Cline CLI with authentication
            result = await self.cli_client.start_run(
                repo_url=project.repo_url,
                ref_type="branch",
                ref=project.default_ref,
                prompt=command.task_prompt,
                provider=settings.cline_provider,
                api_key=settings.cline_api_key,
                model_id=settings.cline_model_id,
                base_url=settings.cline_base_url or None,
                metadata={
                    "slack_channel_id": command.channel_id,
                    "slack_user_id": command.user_id,
                    "run_id": str(run.id)
                }
            )
            
            # Update run with CLI execution details
            run.cline_run_id = result["task_id"]
            run.cline_instance_address = result["instance_address"]
            run.workspace_path = result["workspace_path"]
            run.mark_started()
            await session.commit()
            
            # Store metadata for event streaming
            self._run_metadata[str(run.id)] = {
                "instance_address": result["instance_address"],
                "workspace_path": result["workspace_path"],
                "task_id": result["task_id"]
            }
            
            log_run_event(
                "execution_started",
                str(run.id),
                cline_run_id=result["task_id"],
                instance=result["instance_address"],
                workspace=result["workspace_path"],
                repo_url=project.repo_url
            )
            
            # Start event streaming in background
            await self._start_event_stream(run)
            
            # Post initial status to Slack
            await self._post_initial_slack_message(run, command.response_url)
            
            return run
            
        except Exception as e:
            # Mark run as failed
            run.mark_completed(RunStatus.FAILED, f"Failed to start: {str(e)}")
            await session.commit()
            
            log_run_event("start_failed", str(run.id), error=str(e))
            raise RuntimeError(f"Failed to start run: {e}")
    
    async def cancel_run(self, command: CancelRunCommand, session: AsyncSession) -> bool:
        """
        Cancel a running Cline task.
        
        Args:
            command: Cancel run command
            session: Database session
            
        Returns:
            bool: True if cancellation was successful
        """
        # Find the run
        result = await session.execute(
            select(RunModel).where(RunModel.id == UUID(command.run_id))
        )
        run = result.scalar_one_or_none()
        
        if not run:
            logger.warning(f"Run {command.run_id} not found for cancellation")
            return False
        
        if not run.is_active:
            logger.warning(f"Run {command.run_id} is not active, cannot cancel")
            return False
        
        log_run_event(
            "cancel_requested",
            str(run.id),
            cline_run_id=run.cline_run_id,
            user_id=command.user_id
        )
        
        success = False
        if run.cline_instance_address and run.workspace_path:
            # Cancel via Cline CLI
            success = await self.cli_client.cancel_run(
                run.cline_instance_address,
                run.workspace_path,
                command.reason
            )
        
        if success or not run.cline_run_id:
            # Update database
            run.mark_completed(RunStatus.CANCELLED, f"Cancelled: {command.reason}")
            await session.commit()
            
            # Stop event stream
            await self._stop_event_stream(str(run.id))
            
            # Update Slack
            await self._post_cancellation_update(run)
            
            log_run_event("cancelled", str(run.id), cline_run_id=run.cline_run_id)
        
        return success
    
    async def _resolve_project(
        self, 
        session: AsyncSession, 
        tenant_id: str, 
        channel_id: str
    ) -> Optional[ProjectModel]:
        """
        Resolve project from tenant and channel.
        
        For MVP, we'll create a default project if none exists.
        In production, this would be configured via admin interface.
        """
        result = await session.execute(
            select(ProjectModel).where(
                ProjectModel.tenant_id == tenant_id,
                ProjectModel.slack_channel_id == channel_id
            )
        )
        project = result.scalar_one_or_none()
        
        if not project:
            # Create default project for MVP
            project = ProjectModel(
                tenant_id=tenant_id,
                slack_channel_id=channel_id,
                repo_url="https://github.com/example/demo-repo.git",  # TODO: Make configurable
                default_ref="main"
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            
            logger.info(f"Created default project for channel {channel_id}")
        
        return project
    
    async def _start_event_stream(self, run: RunModel) -> None:
        """Start event streaming for a run in background."""
        if not run.cline_instance_address or not run.workspace_path:
            logger.warning(f"Missing instance/workspace for run {run.id}, cannot start event stream")
            return
        
        # Create background task for event streaming
        task = asyncio.create_task(
            self._handle_event_stream(run),
            name=f"event_stream_{run.id}"
        )
        
        self._active_streams[str(run.id)] = task
        logger.info(f"Started event stream for run {run.id}")
    
    async def _stop_event_stream(self, run_id: str) -> None:
        """Stop event streaming for a run."""
        if run_id in self._active_streams:
            task = self._active_streams[run_id]
            task.cancel()
            del self._active_streams[run_id]
            logger.info(f"Stopped event stream for run {run_id}")
    
    async def _handle_event_stream(self, run: RunModel) -> None:
        """
        Handle event stream for a run.
        
        This runs in the background and processes events from Cline CLI.
        """
        run_id = str(run.id)
        metadata = self._run_metadata.get(run_id)
        
        if not metadata:
            logger.error(f"No metadata found for run {run_id}")
            return
        
        try:
            async for event in self.cli_client.stream_events(
                metadata["instance_address"],
                metadata["workspace_path"],
                metadata["task_id"]
            ):
                await self._process_run_event(run_id, event)
                
        except asyncio.CancelledError:
            logger.info(f"Event stream cancelled for run {run_id}")
        except Exception as e:
            logger.error(f"Error in event stream for run {run_id}: {e}")
            
            # Mark run as failed
            async for session in get_session():
                try:
                    result = await session.execute(
                        select(RunModel).where(RunModel.id == UUID(run_id))
                    )
                    run_obj = result.scalar_one_or_none()
                    if run_obj and run_obj.is_active:
                        run_obj.mark_completed(
                            RunStatus.FAILED, 
                            f"Event stream error: {str(e)}"
                        )
                        await session.commit()
                except Exception as db_error:
                    logger.error(f"Failed to update run status: {db_error}")
    
    async def _process_run_event(self, run_id: str, event: RunEventSchema) -> None:
        """
        Process a single event from Cline Core.
        
        Args:
            run_id: Our internal run ID
            event: Event from Cline Core
        """
        log_run_event(
            "event_received", 
            run_id,
            cline_run_id=event.cline_run_id,
            cli_event_type=event.event_type,  # Renamed to avoid conflict with positional event_type
            message=event.message
        )
        
        # Update database
        async for session in get_session():
            try:
                result = await session.execute(
                    select(RunModel).where(RunModel.id == UUID(run_id))
                )
                run = result.scalar_one_or_none()
                
                if not run:
                    logger.warning(f"Run {run_id} not found for event processing")
                    return
                
                # Update run based on event type
                if event.event_type == "complete":
                    run.mark_completed(RunStatus.SUCCEEDED, event.message)
                elif event.event_type in ("error", "failed"):
                    run.mark_completed(RunStatus.FAILED, event.message)
                elif event.event_type == "cancelled":
                    run.mark_completed(RunStatus.CANCELLED, event.message)
                
                await session.commit()
                
                # Send update to Slack
                await self._post_event_update(run, event)
                
                # Clean up if run is complete
                if run.is_completed:
                    await self._stop_event_stream(run_id)
                    # Clean up Cline instance and workspace
                    run_metadata = self._run_metadata.get(run_id)
                    if run_metadata:
                        await self.cli_client.cleanup_instance(
                            run_metadata["instance_address"],
                            run_metadata["workspace_path"]
                        )
                        del self._run_metadata[run_id]
                    
            except Exception as e:
                logger.error(f"Error processing event for run {run_id}: {e}")
    
    async def _post_initial_slack_message(
        self, 
        run: RunModel, 
        response_url: str
    ) -> None:
        """Post initial status message to Slack."""
        try:
            blocks = self.slack_client.create_run_status_blocks(
                task_prompt=run.task_prompt,
                status="running",
                message="⏳ Starting execution environment...",
                run_id=str(run.id)
            )
            
            await self.slack_client.post_delayed_response(
                response_url=response_url,
                text=f"🚀 Starting Cline run: {run.task_prompt}",
                blocks=blocks,
                replace_original=True
            )
            
        except Exception as e:
            logger.error(f"Failed to post initial Slack message: {e}")
    
    async def _post_event_update(self, run: RunModel, event: RunEventSchema) -> None:
        """Post event update to Slack."""
        try:
            if not run.slack_thread_ts:
                # No thread to update
                return
            
            # Create message based on event type
            if event.event_type == "step":
                # Progress update
                step = int(event.data.get("step", 1))
                total = int(event.data.get("total", 5))
                
                blocks = self.slack_client.create_progress_blocks(
                    task_prompt=run.task_prompt,
                    steps_completed=step - 1,
                    total_steps=total,
                    current_step=event.message,
                    run_id=str(run.id)
                )
                
                # Update the original message
                await self.slack_client.update_message(
                    channel=run.slack_channel_id,
                    ts=run.slack_thread_ts,
                    text=f"🔧 Cline Run: {run.task_prompt}",
                    blocks=blocks
                )
                
            elif event.event_type in ("complete", "error", "failed"):
                # Final status update
                status = "succeeded" if event.event_type == "complete" else "failed"
                
                blocks = self.slack_client.create_run_status_blocks(
                    task_prompt=run.task_prompt,
                    status=status,
                    message=event.message,
                    show_cancel_button=False
                )
                
                await self.slack_client.update_message(
                    channel=run.slack_channel_id,
                    ts=run.slack_thread_ts,
                    text=f"Cline Run: {run.task_prompt}",
                    blocks=blocks
                )
                
        except Exception as e:
            logger.error(f"Failed to post Slack update: {e}")
    
    async def _post_cancellation_update(self, run: RunModel) -> None:
        """Post cancellation update to Slack."""
        try:
            if not run.slack_thread_ts:
                return
            
            blocks = self.slack_client.create_run_status_blocks(
                task_prompt=run.task_prompt,
                status="cancelled",
                message="Run was cancelled by user",
                show_cancel_button=False
            )
            
            await self.slack_client.update_message(
                channel=run.slack_channel_id,
                ts=run.slack_thread_ts,
                text=f"Cline Run: {run.task_prompt}",
                blocks=blocks
            )
            
        except Exception as e:
            logger.error(f"Failed to post cancellation update: {e}")


# Global service instance
_orchestrator_service: Optional[RunOrchestratorService] = None


def get_orchestrator_service() -> RunOrchestratorService:
    """
    Get or create the global orchestrator service instance.
    
    Returns:
        RunOrchestratorService: Service instance
    """
    global _orchestrator_service
    if _orchestrator_service is None:
        _orchestrator_service = RunOrchestratorService()
    return _orchestrator_service


async def cleanup_orchestrator_service():
    """Clean up the global orchestrator service."""
    global _orchestrator_service
    if _orchestrator_service:
        # Cancel all active streams
        for task in _orchestrator_service._active_streams.values():
            task.cancel()
        _orchestrator_service._active_streams.clear()
        _orchestrator_service = None
