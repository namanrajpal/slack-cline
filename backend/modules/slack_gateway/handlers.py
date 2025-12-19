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
from schemas.slack import SlackCommandSchema, SlackInteractivitySchema
from modules.agent.service import get_agent_service
from utils.logging import get_logger, log_slack_event
from utils.slack_client import SlackClient
from .verification import extract_slack_headers, require_slack_verification
from .command_handler import handle_sline_command

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
        if command == "/sline":
            return await handle_sline_command(command_data, background_tasks)
        elif command == "/cline":
            # Legacy support - redirect to /sline
            return JSONResponse(content={
                "response_type": "ephemeral",
                "text": "⚠️ `/cline` has been renamed to `/sline`\n\nPlease use `/sline` instead!"
            })
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
        # Check if bot is @mentioned in ANY message (top-level or thread reply)
        if user_id and text:
            # Slack mentions look like <@USERID>
            bot_user_id = settings.slack_bot_user_id
            bot_mention = f"<@{bot_user_id}>" if bot_user_id else None
            
            if not bot_user_id:
                # Bot user ID not configured - log warning once and skip
                logger.debug("SLACK_BOT_USER_ID not configured, ignoring message")
                return JSONResponse(content={"ok": True})
            
            if bot_mention not in text:
                # Bot not mentioned, ignore this message
                logger.debug(f"Message without @mention, ignoring")
                return JSONResponse(content={"ok": True})
            
            # Strip the @mention from the text before sending to agent
            clean_text = text.replace(bot_mention, "").strip()
            
            # Determine conversation thread_ts:
            # - For thread replies: use existing thread_ts
            # - For top-level messages: use message_ts (creates new thread)
            conversation_thread_ts = thread_ts if thread_ts else message_ts
            
            log_slack_event(
                "mention_received",
                channel_id=channel_id,
                user_id=user_id,
                thread_ts=conversation_thread_ts,
                text=clean_text[:100],
                is_new_conversation=not bool(thread_ts)
            )
            
            # Queue background task to process the message
            # We must respond within 3 seconds, so do actual work in background
            background_tasks.add_task(
                process_thread_reply,
                channel_id=channel_id,
                thread_ts=conversation_thread_ts,  # Use this as conversation ID
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
    Process a thread reply using AgentService.
    
    This runs as a background task after immediately acknowledging to Slack.
    Continues the conversation by sending the message to the agent and posting
    the response back to the thread.
    
    Args:
        channel_id: Slack channel ID
        thread_ts: Thread timestamp (conversation identifier)
        user_id: User who sent the reply
        text: Message text
        message_ts: Message timestamp
    """
    try:
        agent_service = get_agent_service()
        slack_client = SlackClient()
        
        async for session in get_session():
            try:
                # Process message with agent
                response = await agent_service.handle_message(
                    channel_id=channel_id,
                    thread_ts=thread_ts,
                    user_id=user_id,
                    text=text,
                    session=session,
                )
                
                # Post response to Slack thread
                await slack_client.post_message(
                    channel=channel_id,
                    text=response,
                    thread_ts=thread_ts,
                )
                
                logger.info(f"Thread reply processed successfully for thread {thread_ts}")
                break  # Exit after successful processing
                
            except Exception as e:
                logger.error(f"Error processing thread reply: {e}", exc_info=True)
                # Post error to thread
                try:
                    await slack_client.post_message(
                        channel=channel_id,
                        text=f"❌ Sline encountered an error: {str(e)}",
                        thread_ts=thread_ts,
                    )
                except:
                    pass
                break
                
    except Exception as e:
        logger.error(f"Critical error in thread reply processing: {e}", exc_info=True)


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
    
    TODO: Implement interactive actions for future features:
    - Plan approvals (deep-plan mode)
    - Task confirmations
    - Custom workflow triggers
    - Contextual actions (start release, deploy, etc.)
    
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
    
    # Placeholder for future interactivity features
    logger.info(f"Received interactive action: {action_id}")
    
    return JSONResponse(content={
        "text": "🚧 Interactive actions coming soon!\n\n"
                "Future features:\n"
                "• Deep-plan approval workflows\n"
                "• Custom command triggers\n"
                "• Contextual actions (deploy, release, etc.)"
    })
