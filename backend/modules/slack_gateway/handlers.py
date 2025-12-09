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
    
    # Try to parse as JSON first (for Event Subscriptions like message.channels, message.im)
    try:
        payload = json.loads(body.decode('utf-8'))
        event_type = payload.get("type", "")
        
        # URL verification challenge (Event Subscriptions setup)
        if event_type == "url_verification":
            challenge = payload.get("challenge", "")
            logger.info(f"Received URL verification challenge: {challenge[:20]}...")
            return JSONResponse(content={"challenge": challenge})
        
        # Event callbacks (message.channels, message.im, reaction_added, etc.)
        # These are sent when you subscribe to bot events in Slack
        if event_type == "event_callback":
            return await handle_event_callback(payload, background_tasks)
        
        # Other JSON event types we don't handle yet
        logger.debug(f"Ignoring unknown JSON event type: {event_type}")
        return JSONResponse(content={"ok": True})
        
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Not JSON, must be form-encoded slash command - continue normally
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


async def handle_event_callback(payload: Dict[str, Any], background_tasks: BackgroundTasks) -> JSONResponse:
    """
    Handle Slack Event API callbacks (message.channels, message.im, etc.).
    
    This is called when events occur in channels/DMs that the bot is subscribed to.
    Processes thread replies to continue conversations with Cline.
    
    Event payload structure:
    {
        "type": "event_callback",
        "event": {
            "type": "message",  # or "reaction_added", etc.
            "channel": "C1234567890",
            "user": "U1234567890",
            "text": "Hello world",
            "ts": "1234567890.123456",
            "thread_ts": "1234567890.123456"  # Present if this is a thread reply
        },
        "team_id": "T1234567890",
        "event_id": "Ev1234567890"
    }
    
    Args:
        payload: The full event callback payload from Slack
        background_tasks: FastAPI background tasks for async processing
        
    Returns:
        JSONResponse: Acknowledgement response to Slack (must respond within 3 seconds)
    """
    event = payload.get("event", {})
    event_type = event.get("type", "unknown")
    channel_id = event.get("channel", "")
    user_id = event.get("user", "")
    text = event.get("text", "")
    thread_ts = event.get("thread_ts")
    message_ts = event.get("ts", "")
    
    # Ignore bot messages to prevent infinite loops
    # Bot messages have bot_id or subtype="bot_message"
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        return JSONResponse(content={"ok": True})
    
    # Ignore message edits/deletes (subtype indicates these)
    subtype = event.get("subtype", "")
    if subtype in ("message_changed", "message_deleted", "channel_join", "channel_leave"):
        return JSONResponse(content={"ok": True})
    
    # Process message events
    if event_type == "message":
        # Check if this is a thread reply (has thread_ts)
        if thread_ts and user_id and text:
            # Only process if bot is @mentioned in the message
            # Slack mentions look like <@USERID>
            bot_user_id = settings.slack_bot_user_id
            bot_mention = f"<@{bot_user_id}>" if bot_user_id else None
            
            if not bot_user_id:
                # Bot user ID not configured - log warning once and skip
                logger.debug("SLACK_BOT_USER_ID not configured, ignoring thread reply")
                return JSONResponse(content={"ok": True})
            
            if bot_mention not in text:
                # Bot not mentioned, ignore this thread reply
                logger.debug(f"Thread reply without @mention, ignoring (thread: {thread_ts})")
                return JSONResponse(content={"ok": True})
            
            # Strip the @mention from the text before sending to Cline
            clean_text = text.replace(bot_mention, "").strip()
            
            log_slack_event(
                "thread_reply_received",
                channel_id=channel_id,
                user_id=user_id,
                thread_ts=thread_ts,
                text=clean_text[:100]
            )
            
            # Queue background task to process thread reply
            # We must respond within 3 seconds, so do actual work in background
            background_tasks.add_task(
                process_thread_reply,
                channel_id=channel_id,
                thread_ts=thread_ts,
                user_id=user_id,
                text=clean_text,  # Use cleaned text without @mention
                message_ts=message_ts
            )
    
    # Acknowledge quickly - Slack requires 200 OK within 3 seconds
    return JSONResponse(content={"ok": True})


async def process_thread_reply(
    channel_id: str,
    thread_ts: str,
    user_id: str,
    text: str,
    message_ts: str
) -> None:
    """
    Process a thread reply and send it to the corresponding Cline task.
    
    This runs as a background task after immediately acknowledging to Slack.
    
    Flow:
    1. Find run by slack_thread_ts
    2. Check if run is still active and has metadata
    3. Send message to Cline via CLI
    4. Restart event streaming to capture response
    5. Response will be posted back to thread via normal event handling
    
    Args:
        channel_id: Slack channel ID
        thread_ts: Thread timestamp (matches run.slack_thread_ts)
        user_id: User who sent the reply
        text: Message text
        message_ts: Message timestamp
    """
    try:
        orchestrator = get_orchestrator_service()
        
        async for session in get_session():
            try:
                result = await orchestrator.handle_thread_reply(
                    channel_id=channel_id,
                    thread_ts=thread_ts,
                    user_id=user_id,
                    text=text,
                    session=session
                )
                
                if result:
                    logger.info(f"Thread reply processed successfully for thread {thread_ts}")
                else:
                    logger.debug(f"Thread reply not processed (no matching run or run not active) for thread {thread_ts}")
                
                break  # Exit after processing
                
            except Exception as e:
                logger.error(f"Error processing thread reply: {e}", exc_info=True)
                break
                
    except Exception as e:
        logger.error(f"Critical error in thread reply processing: {e}", exc_info=True)


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
