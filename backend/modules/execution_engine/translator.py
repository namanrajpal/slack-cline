"""
Message translator for converting between gRPC protobuf messages and domain models.

This module handles the translation between Cline Core gRPC messages and our
internal domain models, keeping the gRPC details isolated from business logic.
"""

from datetime import datetime
from typing import Dict, Any

from schemas.run import RunEventSchema
from utils.logging import get_logger

logger = get_logger("execution.translator")


def grpc_to_domain_event(grpc_event: Any) -> RunEventSchema:
    """
    Convert a gRPC RunEvent message to a domain RunEventSchema.
    
    Args:
        grpc_event: gRPC RunEvent message (proto object)
        
    Returns:
        RunEventSchema: Domain event model
    """
    try:
        # TODO: Replace with actual proto object access once gRPC is compiled
        # return RunEventSchema(
        #     run_id=grpc_event.run_id,
        #     cline_run_id=grpc_event.run_id,
        #     event_type=grpc_event.event_type,
        #     timestamp=datetime.fromtimestamp(grpc_event.timestamp),
        #     data=dict(grpc_event.data),
        #     message=grpc_event.message
        # )
        
        # Placeholder implementation for testing
        if hasattr(grpc_event, 'run_id'):
            return RunEventSchema(
                run_id=grpc_event.run_id,
                cline_run_id=grpc_event.run_id,
                event_type=getattr(grpc_event, 'event_type', 'status'),
                timestamp=datetime.fromtimestamp(getattr(grpc_event, 'timestamp', datetime.utcnow().timestamp())),
                data=dict(getattr(grpc_event, 'data', {})),
                message=getattr(grpc_event, 'message', '')
            )
        else:
            # Fallback for dict-like objects during development
            return RunEventSchema(
                run_id=grpc_event.get('run_id', ''),
                cline_run_id=grpc_event.get('run_id', ''),
                event_type=grpc_event.get('event_type', 'status'),
                timestamp=datetime.fromtimestamp(grpc_event.get('timestamp', datetime.utcnow().timestamp())),
                data=grpc_event.get('data', {}),
                message=grpc_event.get('message', '')
            )
    
    except Exception as e:
        logger.error(f"Error translating gRPC event to domain model: {e}")
        # Return a fallback event
        return RunEventSchema(
            run_id="unknown",
            cline_run_id="unknown", 
            event_type="error",
            timestamp=datetime.utcnow(),
            data={},
            message=f"Translation error: {str(e)}"
        )


def domain_to_grpc_request(
    repo_url: str,
    ref_type: str,
    ref: str,
    prompt: str,
    metadata: Dict[str, str] = None
) -> Any:
    """
    Convert domain parameters to a gRPC StartRunRequest.
    
    Args:
        repo_url: Git repository URL
        ref_type: Reference type ("branch" or "commit")
        ref: Branch name or commit hash
        prompt: Task description
        metadata: Additional metadata
        
    Returns:
        gRPC StartRunRequest message (proto object)
    """
    try:
        # TODO: Replace with actual proto object creation once gRPC is compiled
        # return cline_pb2.StartRunRequest(
        #     repo_url=repo_url,
        #     ref_type=ref_type,
        #     ref=ref,
        #     prompt=prompt,
        #     metadata=metadata or {}
        # )
        
        # Placeholder implementation - return a dict for now
        return {
            'repo_url': repo_url,
            'ref_type': ref_type,
            'ref': ref,
            'prompt': prompt,
            'metadata': metadata or {}
        }
    
    except Exception as e:
        logger.error(f"Error creating gRPC request: {e}")
        raise ValueError(f"Failed to create gRPC request: {e}")


def domain_to_cancel_request(run_id: str, reason: str = "User requested") -> Any:
    """
    Convert domain parameters to a gRPC CancelRunRequest.
    
    Args:
        run_id: Cline Core run ID
        reason: Cancellation reason
        
    Returns:
        gRPC CancelRunRequest message (proto object)
    """
    try:
        # TODO: Replace with actual proto object creation
        # return cline_pb2.CancelRunRequest(run_id=run_id, reason=reason)
        
        # Placeholder implementation
        return {
            'run_id': run_id,
            'reason': reason
        }
    
    except Exception as e:
        logger.error(f"Error creating cancel request: {e}")
        raise ValueError(f"Failed to create cancel request: {e}")


def grpc_status_to_domain_status(grpc_status: str) -> str:
    """
    Convert gRPC status string to our domain status enum.
    
    Args:
        grpc_status: Status from gRPC response
        
    Returns:
        str: Domain status value
    """
    # Map gRPC statuses to our domain statuses
    status_mapping = {
        'queued': 'queued',
        'running': 'running', 
        'succeeded': 'succeeded',
        'failed': 'failed',
        'cancelled': 'cancelled',
        'completed': 'succeeded',  # Map completed to succeeded
        'error': 'failed',         # Map error to failed
    }
    
    return status_mapping.get(grpc_status.lower(), 'failed')


def extract_run_summary(events: list) -> str:
    """
    Extract a summary from a list of run events.
    
    This analyzes the events from a completed run and generates
    a human-readable summary of what was accomplished.
    
    Args:
        events: List of RunEventSchema objects
        
    Returns:
        str: Summary of the run
    """
    if not events:
        return "Run completed with no events"
    
    try:
        # Find completion or error events
        completion_events = [e for e in events if e.event_type in ('complete', 'error', 'failed')]
        step_events = [e for e in events if e.event_type == 'step']
        
        if completion_events:
            final_event = completion_events[-1]
            if final_event.event_type == 'complete':
                step_count = len(step_events)
                return f"✅ {final_event.message} ({step_count} steps completed)"
            else:
                return f"❌ {final_event.message}"
        
        # Fallback to last event
        last_event = events[-1]
        return f"{last_event.message}"
    
    except Exception as e:
        logger.error(f"Error extracting run summary: {e}")
        return "Run completed"


def map_event_to_slack_emoji(event_type: str) -> str:
    """
    Map event types to appropriate Slack emojis for visual feedback.
    
    Args:
        event_type: Event type from Cline Core
        
    Returns:
        str: Emoji for the event type
    """
    emoji_mapping = {
        'status': '⏳',
        'step': '🔧',
        'log': '📝',
        'error': '❌',
        'complete': '✅',
        'cancelled': '⏹️',
        'failed': '💥'
    }
    
    return emoji_mapping.get(event_type, '🔍')
