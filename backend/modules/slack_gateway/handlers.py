"""
Slack Gateway HTTP endpoint handlers.

This module contains FastAPI endpoint handlers for Slack webhooks including
slash commands and interactive components. It handles request validation,
signature verification, and conversion to internal commands.
"""

import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse

from config import settings
from database import get_session
from schemas.slack import SlackCommandSchema, SlackInteractivitySchema, StartRunCommand, CancelRunCommand
from modules.orchestrator.service import get_orchestrator_service
from utils.logging import get_logger, log_slack_event
from .verification import extract_slack_headers, require_slack_verification

logger = get_logger("slack.gateway")

# Create router for Slack endpoints
slack_router = APIRouter()


@slack_router.get("/health")
async def slack_health():
    """Health check for Slack Gateway module."""
    return {"status": "healthy", "module": "slack_gateway"}


@slack_router.post("/events")
async def handle_slack_events(
    request: Request,
    # Slack sends slash commands as form data
    token: str = Form(...),
    team_id: str = Form(...),
    team_domain: str = Form(...), 
    channel_id: str = Form(...),
    channel_name: str = Form(...),
    user_id: str = Form(...),
    user_name: str = Form(...),
    command: str = Form(...),
    text: str = Form(default=""),
    response_url: str = Form(...),
    trigger_id: str = Form(...)
):
    """
    Handle Slack slash commands like `/cline run <task>`.
    
    This endpoint receives slash command webhooks from Slack and processes them
    into internal command objects for the Run Orchestrator.
    """
    # Get raw body for signature verification
    body = await request.body()
    timestamp, signature = extract_slack_headers(request)
    
    # Verify Slack signature
    require_slack_verification(timestamp, body, signature)
    
    log_slack_event(
        "slash_command_received",
        channel_id=channel_id,
        user_id=user_id,
        command=command,
        text=text
    )
    
    try:
        # Validate command payload
        command_data = SlackCommandSchema(
            token=token,
            team_id=team_id,
            team_domain=team_domain,
            channel_id=channel_id,
            channel_name=channel_name,
            user_id=user_id,
            user_name=user_name,
            command=command,
            text=text,
            response_url=response_url,
            trigger_id=trigger_id
        )
        
        # Handle different command types
        if command == "/cline":
            return await handle_cline_command(command_data)
        else:
            logger.warning(f"Unknown command: {command}")
            return JSONResponse(
                content={
                    "response_type": "ephemeral",
                    "text": f"Unknown command: {command}"
                }
            )
    
    except Exception as e:
        logger.error(f"Error processing slash command: {e}", exc_info=True)
        return JSONResponse(
            status_code=200,  # Still return 200 to Slack
            content={
                "response_type": "ephemeral",
                "text": "❌ An error occurred processing your command. Please try again."
            }
        )


async def handle_cline_command(command_data: SlackCommandSchema) -> JSONResponse:
    """
    Handle `/cline` slash command.
    
    Parses the command text and routes to appropriate subcommand handler.
    
    Args:
        command_data: Validated command data from Slack
        
    Returns:
        JSONResponse: Response to send back to Slack
    """
    text = command_data.text.strip()
    
    if not text:
        return JSONResponse(content={
            "response_type": "ephemeral",
            "text": "Usage: `/cline run <task description>`\nExample: `/cline run fix failing unit tests`"
        })
    
    # Parse command and arguments
    parts = text.split(maxsplit=1)
    subcommand = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    
    if subcommand == "run":
        return await handle_run_command(command_data, args)
    elif subcommand == "status":
        return await handle_status_command(command_data)
    elif subcommand == "help":
        return await handle_help_command()
    else:
        return JSONResponse(content={
            "response_type": "ephemeral",
            "text": f"Unknown subcommand: `{subcommand}`\nUse `/cline help` for available commands."
        })


async def handle_run_command(command_data: SlackCommandSchema, task_prompt: str) -> JSONResponse:
    """
    Handle `/cline run <task>` command.
    
    Creates a StartRunCommand and delegates to the Run Orchestrator.
    
    Args:
        command_data: Validated command data from Slack
        task_prompt: Task description provided by user
        
    Returns:
        JSONResponse: Immediate response to Slack
    """
    if not task_prompt.strip():
        return JSONResponse(content={
            "response_type": "ephemeral", 
            "text": "Please provide a task description.\nExample: `/cline run fix failing unit tests`"
        })
    
    try:
        # Create internal command for orchestrator
        start_command = StartRunCommand(
            tenant_id=settings.default_tenant_id,  # TODO: Extract from team_id when multi-tenant
            channel_id=command_data.channel_id,
            user_id=command_data.user_id,
            task_prompt=task_prompt,
            response_url=command_data.response_url,
            trigger_id=command_data.trigger_id
        )
        
        log_slack_event(
            "run_command_created",
            channel_id=command_data.channel_id,
            user_id=command_data.user_id,
            task_prompt=task_prompt[:100]  # Truncate for logging
        )
        
        # Send to Run Orchestrator
        orchestrator = get_orchestrator_service()
        
        async for session in get_session():
            try:
                run = await orchestrator.start_run(start_command, session)
                
                # Return immediate response - the orchestrator will post updates
                return JSONResponse(content={
                    "response_type": "in_channel",
                    "text": f"🚀 Starting Cline run: `{task_prompt}`",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"🚀 Starting Cline run: `{task_prompt}`"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn", 
                                "text": "⏳ Setting up execution environment..."
                            }
                        }
                    ]
                })
                
            except ValueError as e:
                # Project not found error
                return JSONResponse(content={
                    "response_type": "ephemeral",
                    "text": f"❌ Configuration error: {str(e)}\nPlease contact your admin to set up this channel."
                })
            except Exception as e:
                # Other errors
                logger.error(f"Failed to start run: {e}")
                return JSONResponse(content={
                    "response_type": "ephemeral",
                    "text": "❌ Failed to start run. Please try again or contact support."
                })
        
    except Exception as e:
        logger.error(f"Error creating run command: {e}", exc_info=True)
        return JSONResponse(content={
            "response_type": "ephemeral",
            "text": "❌ Failed to start run. Please try again."
        })


async def handle_status_command(command_data: SlackCommandSchema) -> JSONResponse:
    """Handle `/cline status` command to show active runs."""
    # TODO: Query active runs from database
    return JSONResponse(content={
        "response_type": "ephemeral",
        "text": "📊 Run Status\nNo active runs in this channel."
    })


async def handle_help_command() -> JSONResponse:
    """Handle `/cline help` command."""
    return JSONResponse(content={
        "response_type": "ephemeral",
        "text": """🤖 **Cline Commands**

`/cline run <task>` - Start a new Cline run with the given task
`/cline status` - Show active runs in this channel  
`/cline help` - Show this help message

**Examples:**
• `/cline run fix failing unit tests`
• `/cline run add user authentication to the login page`
• `/cline run update README with installation instructions`
"""
    })


@slack_router.post("/interactivity") 
async def handle_slack_interactivity(request: Request):
    """
    Handle Slack interactive components like button clicks.
    
    This endpoint receives webhooks when users interact with buttons,
    menus, or other interactive elements in Slack messages.
    """
    # Get raw body for signature verification
    body = await request.body()
    timestamp, signature = extract_slack_headers(request)
    
    # Verify Slack signature
    require_slack_verification(timestamp, body, signature)
    
    try:
        # Slack sends interactivity payload as form-encoded JSON
        form_data = await request.form()
        payload_str = form_data.get("payload", "")
        payload = json.loads(payload_str)
        
        # Validate payload
        interactivity_data = SlackInteractivitySchema(**payload)
        
        log_slack_event(
            "interactivity_received",
            channel_id=payload.get("channel", {}).get("id"),
            user_id=payload.get("user", {}).get("id"),
            action_type=payload.get("type")
        )
        
        # Handle different interaction types
        if interactivity_data.type == "block_actions":
            return await handle_block_actions(interactivity_data, payload)
        else:
            logger.warning(f"Unhandled interaction type: {interactivity_data.type}")
            return JSONResponse(content={"text": "Action not supported"})
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in interactivity payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    except Exception as e:
        logger.error(f"Error processing interactivity: {e}", exc_info=True)
        return JSONResponse(content={"text": "❌ An error occurred processing your action."})


async def handle_block_actions(interactivity_data: SlackInteractivitySchema, payload: Dict[str, Any]) -> JSONResponse:
    """
    Handle block action interactions like button clicks.
    
    Args:
        interactivity_data: Validated interactivity payload
        payload: Raw payload for accessing action details
        
    Returns:
        JSONResponse: Response to update the message
    """
    actions = payload.get("actions", [])
    if not actions:
        return JSONResponse(content={"text": "No actions found"})
    
    action = actions[0]  # Handle first action
    action_id = action.get("action_id")
    
    if action_id == "cancel_run":
        return await handle_cancel_run_action(interactivity_data, action)
    else:
        logger.warning(f"Unhandled action_id: {action_id}")
        return JSONResponse(content={"text": f"Action `{action_id}` not supported"})


async def handle_cancel_run_action(interactivity_data: SlackInteractivitySchema, action: Dict[str, Any]) -> JSONResponse:
    """
    Handle cancel run button click.
    
    Args:
        interactivity_data: Validated interactivity payload
        action: Action details from the button click
        
    Returns:
        JSONResponse: Response to update the message
    """
    run_id = action.get("value", "")  # TODO: Use actual run ID
    user_id = interactivity_data.user.get("id", "")
    
    try:
        # Create cancel command
        cancel_command = CancelRunCommand(
            run_id=run_id,
            user_id=user_id,
            reason="Cancelled by user"
        )
        
        log_slack_event(
            "cancel_run_requested",
            user_id=user_id,
            run_id=run_id
        )
        
        # Send to Run Orchestrator
        orchestrator = get_orchestrator_service()
        
        async for session in get_session():
            try:
                success = await orchestrator.cancel_run(cancel_command, session)
                
                if success:
                    # Update the message to show cancellation
                    return JSONResponse(content={
                        "replace_original": True,
                        "text": "❌ Run cancelled by user",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "❌ Run cancelled by user"
                                }
                            }
                        ]
                    })
                else:
                    return JSONResponse(content={
                        "text": "❌ Failed to cancel run"
                    })
            except Exception as e:
                logger.error(f"Error cancelling run: {e}")
                return JSONResponse(content={
                    "text": "❌ Error occurred while cancelling run"
                })

        # Fallback response
        return JSONResponse(content={
            "replace_original": True,
            "text": "❌ Run cancelled by user",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "❌ Run cancelled by user"
                    }
                }
            ]
        })
        
    except Exception as e:
        logger.error(f"Error cancelling run: {e}", exc_info=True)
        return JSONResponse(content={"text": "❌ Failed to cancel run"})
