"""
Execution Engine gRPC client for communicating with Cline Core.

This module provides a high-level interface for starting runs, streaming events,
and managing the lifecycle of Cline executions via gRPC.

IMPORTANT: Before using this module, you must compile the proto files:
    cd backend && python compile_protos.py
"""

import asyncio
import json
from typing import AsyncIterator, Dict, Optional
from datetime import datetime

import grpc
from grpc import aio

from config import settings
from schemas.run import RunEventSchema
from utils.logging import get_logger, log_grpc_event

# Import generated gRPC code
# NOTE: These imports will work after running: python backend/compile_protos.py
try:
    from proto.cline import task_pb2, task_pb2_grpc
    from proto.cline import state_pb2, state_pb2_grpc
    from proto.cline import ui_pb2, ui_pb2_grpc
    from proto.cline import common_pb2
    GRPC_AVAILABLE = True
except ImportError as e:
    # Graceful fallback if protos haven't been compiled yet
    GRPC_AVAILABLE = False
    import warnings
    warnings.warn(
        f"gRPC proto modules not found: {e}\n"
        "Run 'python backend/compile_protos.py' to generate them.\n"
        "Falling back to mock mode for development."
    )

logger = get_logger("execution.client")


class ExecutionEngineClient:
    """
    Client for communicating with Cline Core via gRPC.
    
    This client provides a high-level async interface for starting runs,
    streaming events, and managing Cline executions using the actual
    Cline Core gRPC services.
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        timeout: int = None
    ):
        """
        Initialize the execution engine client.
        
        Args:
            host: Cline Core gRPC server host (defaults to config)
            port: Cline Core gRPC server port (defaults to config)  
            timeout: gRPC call timeout in seconds (defaults to config)
        """
        self.host = host or settings.cline_core_host
        self.port = port or settings.cline_core_port
        self.timeout = timeout or settings.cline_core_timeout
        self.address = f"{self.host}:{self.port}"
        
        self._channel: Optional[aio.Channel] = None
        self._task_stub = None
        self._state_stub = None
        self._ui_stub = None
        
        logger.info(f"Initialized execution engine client for {self.address}")
    
    async def connect(self) -> None:
        """Establish gRPC connection to Cline Core."""
        if self._channel is None:
            if not GRPC_AVAILABLE:
                logger.warning(
                    "gRPC proto modules not compiled. "
                    "Run 'python backend/compile_protos.py' first."
                )
                return
            
            # Create async gRPC channel
            self._channel = aio.insecure_channel(
                self.address,
                options=[
                    ('grpc.max_receive_message_length', 100 * 1024 * 1024),  # 100MB
                    ('grpc.max_send_message_length', 100 * 1024 * 1024),
                    ('grpc.keepalive_time_ms', 30000),
                    ('grpc.keepalive_timeout_ms', 10000),
                ]
            )
            
            # Create service stubs
            self._task_stub = task_pb2_grpc.TaskServiceStub(self._channel)
            self._state_stub = state_pb2_grpc.StateServiceStub(self._channel)
            self._ui_stub = ui_pb2_grpc.UiServiceStub(self._channel)
            
            logger.info(f"Connected to Cline Core at {self.address}")
    
    async def disconnect(self) -> None:
        """Close gRPC connection."""
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._task_stub = None
            self._state_stub = None
            self._ui_stub = None
            logger.info("Disconnected from Cline Core")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def start_run(
        self,
        repo_url: str,
        ref_type: str,
        ref: str,
        prompt: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Start a new Cline run using TaskService.newTask().
        
        Args:
            repo_url: Git repository URL
            ref_type: Reference type ("branch" or "commit")
            ref: Branch name or commit hash
            prompt: Task description
            metadata: Additional metadata for the run
            
        Returns:
            str: Cline Core task ID
            
        Raises:
            RuntimeError: If the run fails to start
        """
        start_time = datetime.utcnow()
        
        try:
            await self.connect()
            
            if not GRPC_AVAILABLE or not self._task_stub:
                # Fallback to mock for development
                logger.warning("Using mock implementation (gRPC not available)")
                import uuid
                return f"mock_task_{uuid.uuid4().hex[:8]}"
            
            # Create gRPC request using actual Cline proto
            # Note: Cline's newTask expects prompt in 'text' field
            # We prepend repo/ref info to the prompt since Cline doesn't
            # have separate repo parameters in the newTask RPC
            full_prompt = f"Repository: {repo_url}\nBranch: {ref}\n\nTask: {prompt}"
            
            request = task_pb2.NewTaskRequest(
                text=full_prompt,
                images=[],  # Could be extended to support images
                files=[],   # Could be extended to support file attachments
                task_settings=None  # Could include mode, model settings, etc.
            )
            
            # Call Cline Core TaskService.newTask()
            response = await self._task_stub.NewTask(
                request,
                timeout=self.timeout
            )
            
            task_id = response.value
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_grpc_event("TaskService.NewTask", True, duration, task_id=task_id)
            
            logger.info(f"Started Cline task {task_id} for repo {repo_url}")
            return task_id
            
        except grpc.RpcError as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_grpc_event("TaskService.NewTask", False, duration, error=str(e))
            logger.error(f"gRPC error starting task: {e.code()} - {e.details()}")
            raise RuntimeError(f"Failed to start Cline task: {e.details()}")
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_grpc_event("TaskService.NewTask", False, duration, error=str(e))
            logger.error(f"Failed to start task: {e}")
            raise RuntimeError(f"Failed to start Cline task: {e}")
    
    async def stream_events(self, task_id: str) -> AsyncIterator[RunEventSchema]:
        """
        Stream events from a Cline task using StateService.subscribeToState().
        
        Cline uses a state-based model where all messages are in the state JSON.
        We subscribe to state updates and extract new messages from each update.
        
        Args:
            task_id: Cline Core task ID
            
        Yields:
            RunEventSchema: Events from the running task
        """
        logger.info(f"Starting event stream for task {task_id}")
        
        try:
            await self.connect()
            
            if not GRPC_AVAILABLE or not self._state_stub:
                # Fallback to mock events for development
                logger.warning("Using mock event stream (gRPC not available)")
                async for event in self._mock_event_stream(task_id):
                    yield event
                return
            
            # Subscribe to state updates
            request = state_pb2.EmptyRequest()
            stream = self._state_stub.SubscribeToState(request, timeout=self.timeout)
            
            # Track which messages we've already yielded
            seen_messages = set()
            
            async for state_update in stream:
                # Extract messages from state JSON
                messages = self._extract_messages_from_state(state_update.state_json)
                
                # Yield new messages as events
                for msg in messages:
                    msg_id = f"{msg.get('ts', 0)}"
                    if msg_id not in seen_messages:
                        seen_messages.add(msg_id)
                        
                        # Convert Cline message to our event schema
                        event = self._message_to_event(task_id, msg)
                        if event:
                            yield event
                            log_grpc_event(
                                "StateService.SubscribeToState", 
                                True, 
                                event_type=event.event_type
                            )
                        
                        # Check for completion
                        if msg.get('say') == 'completion_result':
                            logger.info(f"Task {task_id} completed")
                            break
            
        except grpc.RpcError as e:
            log_grpc_event("StateService.SubscribeToState", False, error=str(e))
            logger.error(f"gRPC error streaming events: {e.code()} - {e.details()}")
            raise
        except Exception as e:
            log_grpc_event("StateService.SubscribeToState", False, error=str(e))
            logger.error(f"Error streaming events for task {task_id}: {e}")
            raise
    
    def _extract_messages_from_state(self, state_json: str) -> list:
        """
        Extract messages from Cline's state JSON.
        
        State structure:
        {
          "clineMessages": [
            {"ts": 123456, "type": "say", "say": "text", "text": "...", "partial": false},
            {"ts": 123457, "type": "ask", "ask": "command", "text": "...", "partial": false}
          ],
          "currentTaskItem": {"id": "task_123", ...},
          "mode": "plan"
        }
        """
        try:
            state = json.loads(state_json)
            return state.get('clineMessages', [])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse state JSON: {e}")
            return []
    
    def _message_to_event(self, task_id: str, msg: dict) -> Optional[RunEventSchema]:
        """
        Convert a Cline message to a RunEventSchema.
        
        Args:
            task_id: Task ID
            msg: Cline message dict
            
        Returns:
            RunEventSchema or None if message should be skipped
        """
        # Skip partial messages (they're streamed via UiService)
        if msg.get('partial', False):
            return None
        
        msg_type = msg.get('type', '')
        timestamp = datetime.fromtimestamp(msg.get('ts', 0) / 1000.0)
        text = msg.get('text', '')
        
        # Determine event type
        if msg_type == 'say':
            say_type = msg.get('say', '')
            if say_type == 'completion_result':
                event_type = 'complete'
            elif say_type == 'error':
                event_type = 'error'
            elif say_type == 'text':
                event_type = 'step'
            else:
                event_type = 'status'
        elif msg_type == 'ask':
            event_type = 'ask'
        else:
            event_type = 'status'
        
        return RunEventSchema(
            run_id=task_id,
            cline_run_id=task_id,
            event_type=event_type,
            timestamp=timestamp,
            data={'cline_msg': msg},
            message=text or f"{msg_type}: {msg.get('say', msg.get('ask', ''))}"
        )
    
    async def cancel_run(self, task_id: str, reason: str = "User requested") -> bool:
        """
        Cancel a running Cline task using TaskService.cancelTask().
        
        Args:
            task_id: Cline Core task ID
            reason: Reason for cancellation
            
        Returns:
            bool: True if cancellation was successful
        """
        start_time = datetime.utcnow()
        
        try:
            await self.connect()
            
            if not GRPC_AVAILABLE or not self._task_stub:
                logger.warning("Using mock cancel (gRPC not available)")
                return True
            
            # Call Cline Core TaskService.cancelTask()
            request = task_pb2.EmptyRequest()
            await self._task_stub.CancelTask(request, timeout=self.timeout)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_grpc_event("TaskService.CancelTask", True, duration, task_id=task_id)
            
            logger.info(f"Cancelled task {task_id}: {reason}")
            return True
            
        except grpc.RpcError as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_grpc_event("TaskService.CancelTask", False, duration, error=str(e))
            logger.error(f"gRPC error cancelling task: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_grpc_event("TaskService.CancelTask", False, duration, error=str(e))
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False
    
    async def get_run_status(self, task_id: str) -> Dict[str, any]:
        """
        Get the status of a Cline task using StateService.getLatestState().
        
        Args:
            task_id: Cline Core task ID
            
        Returns:
            dict: Run status information
        """
        start_time = datetime.utcnow()
        
        try:
            await self.connect()
            
            if not GRPC_AVAILABLE or not self._state_stub:
                logger.warning("Using mock status (gRPC not available)")
                return {
                    "run_id": task_id,
                    "status": "running",
                    "message": "Task is being executed (mock)",
                    "started_at": datetime.utcnow(),
                    "finished_at": None
                }
            
            # Get current state
            request = state_pb2.EmptyRequest()
            response = await self._state_stub.GetLatestState(request, timeout=self.timeout)
            
            # Parse state to determine status
            state = json.loads(response.state_json)
            messages = state.get('clineMessages', [])
            
            # Determine status from messages
            status = "running"
            if messages:
                last_msg = messages[-1]
                if last_msg.get('say') == 'completion_result':
                    status = "succeeded"
                elif last_msg.get('say') == 'error':
                    status = "failed"
            
            status_info = {
                "run_id": task_id,
                "status": status,
                "message": f"Task status: {status}",
                "started_at": datetime.utcnow(),
                "finished_at": datetime.utcnow() if status in ('succeeded', 'failed') else None
            }
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_grpc_event("StateService.GetLatestState", True, duration, task_id=task_id)
            
            return status_info
            
        except grpc.RpcError as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_grpc_event("StateService.GetLatestState", False, duration, error=str(e))
            logger.error(f"gRPC error getting status: {e.code()} - {e.details()}")
            raise
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_grpc_event("StateService.GetLatestState", False, duration, error=str(e))
            logger.error(f"Error getting status for task {task_id}: {e}")
            raise
    
    async def _mock_event_stream(self, task_id: str) -> AsyncIterator[RunEventSchema]:
        """
        Mock event stream for development when gRPC is not available.
        
        This simulates what real Cline Core event streaming would look like.
        """
        events = [
            {"event_type": "status", "message": "Cloning repository..."},
            {"event_type": "step", "message": "Analyzing codebase..."},
            {"event_type": "step", "message": "Running tests..."},
            {"event_type": "step", "message": "Making changes..."},
            {"event_type": "complete", "message": "Task completed successfully"}
        ]
        
        for i, event_data in enumerate(events):
            await asyncio.sleep(2)  # Simulate processing time
            
            yield RunEventSchema(
                run_id=task_id,
                cline_run_id=task_id,
                event_type=event_data["event_type"],
                timestamp=datetime.utcnow(),
                data={"step": str(i + 1), "total": str(len(events))},
                message=event_data["message"]
            )


# Global client instance for dependency injection
_execution_client: Optional[ExecutionEngineClient] = None


def get_execution_client() -> ExecutionEngineClient:
    """
    Get or create the global execution client instance.
    
    Returns:
        ExecutionEngineClient: Client instance
    """
    global _execution_client
    if _execution_client is None:
        _execution_client = ExecutionEngineClient()
    return _execution_client


async def cleanup_execution_client():
    """Clean up the global execution client."""
    global _execution_client
    if _execution_client:
        await _execution_client.disconnect()
        _execution_client = None
