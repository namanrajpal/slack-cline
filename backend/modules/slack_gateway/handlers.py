"""
Slack Gateway HTTP endpoint handlers.

This module contains FastAPI endpoint handlers for Slack webhooks including
slash commands and interactive components. It handles request validation,
signature verification, and conversion to internal commands.
"""

import json
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request, status
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
async def handle_slack_events(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Slack events including slash commands and event subscriptions.
    
    This endpoint receives:
    1. URL verification challenges (Event Subscriptions setup)
    2. Slash command webhooks from Slack
    3. Event callbacks (messages, reactions, etc.)
    """
    # Get raw body ONCE for both signature verification and parsing
    body = await request.body()
    
    # Check for URL verification challenge (Event Subscriptions setup)
    # This happens when you configure Event Subscriptions in Slack
    try:
        payload = json.loads(body.decode('utf-8'))
        if payload.get("type") == "url_verification":
            challenge = payload.get("challenge", "")
            logger.info(f"Received URL verification challenge: {challenge[:20]}...")
            return JSONResponse(content={"challenge": challenge})
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Not JSON, probably form-encoded slash command - continue normally
        pass
    
    timestamp, signature = extract_slack_headers(request)
    
    # Verify Slack signature with raw body
    require_slack_verification(timestamp, body, signature)
    
    # Parse form data from body (manually to avoid double-read)
    form_data = {}
    try:
        form_str = body.decode('utf-8')
        from urllib.parse import parse_qs
        parsed = parse_qs(form_str)
        # parse_qs returns lists, so get first value of each
        form_data = {k: v[0] if v else "" for k, v in parsed.items()}
    except Exception as e:
        logger.error(f"Failed to parse form data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid form data"
        )
    
    # Extract form fields
    token = form_data.get('token', '')
    team_id = form_data.get('team_id', '')
    team_domain = form_data.get('team_domain', '')
    channel_id = form_data.get('channel_id', '')
    channel_name = form_data.get('channel_name', '')
    user_id = form_data.get('user_id', '')
    user_name = form_data.get('user_name', '')
    command = form_data.get('command', '')
    text = form_data.get('text', '')
    response_url = form_data.get('response_url', '')
    trigger_id = form_data.get('trigger_id', '')
    
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
            return await handle_cline_command(command_data, background_tasks)
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


async def handle_cline_command(command_data: SlackCommandSchema, background_tasks: BackgroundTasks) -> JSONResponse:
    """
    Handle `/cline` slash command.
    
    Parses the command text and routes to appropriate subcommand handler.
    
    Args:
        command_data: Validated command data from Slack
        background_tasks: FastAPI background tasks for async processing
        
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
        return await handle_run_command(command_data, args, background_tasks)
    elif subcommand == "status":
        return await handle_status_command(command_data)
    elif subcommand == "github":
        return await handle_github_command(command_data)
    elif subcommand == "help":
        return await handle_help_command()
    else:
        return JSONResponse(content={
            "response_type": "ephemeral",
            "text": f"Unknown subcommand: `{subcommand}`\nUse `/cline help` for available commands."
        })


async def start_run_background(start_command: StartRunCommand):
    """
    Background worker to start a Cline run.
    
    This runs asynchronously after returning immediate acknowledgement to Slack.
    Posts updates via Slack's response_url.
    
    Args:
        start_command: Command with run parameters
    """
    try:
        orchestrator = get_orchestrator_service()
        
        async for session in get_session():
            try:
                run = await orchestrator.start_run(start_command, session)
                logger.info(f"Background task successfully started run {run.id}")
                break  # Exit after successful start
            except Exception as e:
                logger.error(f"Background task failed to start run: {e}", exc_info=True)
                # TODO: Post error to response_url if available
                break
                
    except Exception as e:
        logger.error(f"Critical error in background task: {e}", exc_info=True)


async def handle_run_command(command_data: SlackCommandSchema, task_prompt: str, background_tasks: BackgroundTasks) -> JSONResponse:
    """
    Handle `/cline run <task>` command.
    
    Returns immediate acknowledgement to Slack (< 3 seconds), then queues
    the actual work as a background task.
    
    Args:
        command_data: Validated command data from Slack
        task_prompt: Task description provided by user
        background_tasks: FastAPI background tasks
        
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
            tenant_id=settings.default_tenant_id,
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
            task_prompt=task_prompt[:100]
        )
        
        # Queue background task (non-blocking)
        background_tasks.add_task(start_run_background, start_command)
        
        # Return immediate acknowledgement (under 3 seconds!)
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


async def handle_github_command(command_data: SlackCommandSchema) -> JSONResponse:
    """Handle `/cline github` command to connect GitHub account."""
    # Build GitHub OAuth URL with user info
    oauth_url = (
        f"{settings.app_base_url}/auth/github/login"
        f"?tenant_id={settings.default_tenant_id}"
        f"&slack_user_id={command_data.user_id}"
        f"&slack_username={command_data.user_name}"
    )
    
    return JSONResponse(content={
        "response_type": "ephemeral",
        "text": "⚙️ Cline Settings",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚙️ Cline Settings"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Connect your GitHub account*\n\nCommits made by Cline will be attributed to you. This requires GitHub authentication."
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🔗 Connect GitHub"
                        },
                        "style": "primary",
                        "url": oauth_url
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "ℹ️ This will open a browser window to authorize with GitHub."
                    }
                ]
            }
        ]
    })


async def handle_help_command() -> JSONResponse:
    """Handle `/cline help` command."""
    return JSONResponse(content={
        "response_type": "ephemeral",
        "text": """🤖 **Cline Commands**

`/cline run <task>` - Start a new Cline run with the given task
`/cline github` - Connect your GitHub account for commit attribution
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
    
    if action_id == "approve_plan":
        return await handle_approve_plan_action(interactivity_data, action)
    elif action_id == "cancel_run":
        return await handle_cancel_run_action(interactivity_data, action)
    else:
        logger.warning(f"Unhandled action_id: {action_id}")
        return JSONResponse(content={"text": f"Action `{action_id}` not supported"})


async def handle_approve_plan_action(interactivity_data: SlackInteractivitySchema, action: Dict[str, Any]) -> JSONResponse:
    """
    Handle approve plan button click.
    
    Args:
        interactivity_data: Validated interactivity payload
        action: Action details from the button click
        
    Returns:
        JSONResponse: Response to update the message
    """
    run_id = action.get("value", "")
    user_id = interactivity_data.user.get("id", "")
    
    try:
        log_slack_event(
            "approve_plan_requested",
            user_id=user_id,
            run_id=run_id
        )
        
        # Send to Run Orchestrator
        orchestrator = get_orchestrator_service()
        
        async for session in get_session():
            try:
                success = await orchestrator.approve_run(run_id, session)
                
                if success:
                    # Update the message to show approval + execution started
                    return JSONResponse(content={
                        "replace_original": True,
                        "text": "✅ Plan approved - Executing...",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "✅ Plan approved by user"
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "🚀 Executing plan autonomously..."
                                }
                            }
                        ]
                    })
                else:
                    return JSONResponse(content={
                        "text": "❌ Failed to approve plan"
                    })
            except Exception as e:
                logger.error(f"Error approving plan: {e}")
                return JSONResponse(content={
                    "text": "❌ Error occurred while approving plan"
                })

        # Fallback response
        return JSONResponse(content={
            "text": "❌ Failed to approve plan"
        })
        
    except Exception as e:
        logger.error(f"Error approving plan: {e}", exc_info=True)
        return JSONResponse(content={"text": "❌ Failed to approve plan"})


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
