"""
Slack slash command handler for /sline commands.

This module handles /sline slash commands and routes them to the agent service,
similar to @mentions. It provides a centralized, extensible command dispatcher
that can be configured via the dashboard in the future.
"""

from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse

from database import get_session
from schemas.slack import SlackCommandSchema
from modules.agent.service import get_agent_service
from utils.logging import get_logger, log_slack_event
from utils.slack_client import SlackClient

logger = get_logger("slack.commands")


async def handle_sline_command(
    command_data: SlackCommandSchema,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """
    Handle /sline slash command.
    
    Routes commands to the appropriate handler based on the text.
    Primary interaction is via agent - user can send any prompt just like @mentions.
    
    Args:
        command_data: Validated command data from Slack
        background_tasks: FastAPI background tasks for async processing
        
    Returns:
        JSONResponse: Response to send back to Slack
    """
    text = command_data.text.strip()
    
    # If no text, show help
    if not text:
        return await handle_help()
    
    # Check for utility commands
    parts = text.split(maxsplit=1)
    subcommand = parts[0].lower()
    
    if subcommand == "help":
        return await handle_help()
    elif subcommand == "status":
        return await handle_status(command_data)
    else:
        # Default: treat entire text as a prompt to the agent
        return await dispatch_to_agent(
            channel_id=command_data.channel_id,
            user_id=command_data.user_id,
            text=text,
            background_tasks=background_tasks
        )


async def dispatch_to_agent(
    channel_id: str,
    user_id: str,
    text: str,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """
    Dispatch a prompt to the Sline agent (same as @mention flow).
    
    Posts an initial message to Slack and processes the prompt in the background,
    similar to how @mentions work.
    
    Args:
        channel_id: Slack channel ID
        user_id: User who issued the command
        text: Prompt text
        background_tasks: FastAPI background tasks
        
    Returns:
        JSONResponse: Empty response (message posted directly to Slack)
    """
    try:
        log_slack_event(
            "sline_command_received",
            channel_id=channel_id,
            user_id=user_id,
            text=text[:100]
        )
        
        # Post initial message to Slack to get thread_ts
        slack_client = SlackClient()
        initial_message = await slack_client.post_message(
            channel=channel_id,
            text=f"🤖 Working on: `{text}`",
        )
        
        # Get the thread timestamp from the response
        thread_ts = initial_message.get("ts", "")
        
        if not thread_ts:
            logger.error("Failed to get thread timestamp from Slack")
            return JSONResponse(content={
                "response_type": "ephemeral",
                "text": "❌ Failed to create thread. Please try again."
            })
        
        # Queue background task to process with agent (non-blocking)
        background_tasks.add_task(
            process_agent_prompt,
            channel_id=channel_id,
            thread_ts=thread_ts,
            user_id=user_id,
            text=text
        )
        
        # Return empty response (message already posted)
        return JSONResponse(content={})
        
    except Exception as e:
        logger.error(f"Error handling /sline command: {e}", exc_info=True)
        return JSONResponse(content={
            "response_type": "ephemeral",
            "text": "❌ Failed to start. Please try again."
        })


async def process_agent_prompt(
    channel_id: str,
    thread_ts: str,
    user_id: str,
    text: str
) -> None:
    """
    Process a prompt using the agent service (background task).
    
    This runs asynchronously after immediately acknowledging to Slack.
    
    Args:
        channel_id: Slack channel ID
        thread_ts: Thread timestamp for posting responses
        user_id: User who sent the command
        text: Prompt text
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
                
                logger.info(f"Agent response posted to thread {thread_ts}")
                break  # Exit after successful processing
                
            except Exception as e:
                logger.error(f"Error processing /sline command: {e}", exc_info=True)
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
        logger.error(f"Critical error in /sline processing: {e}", exc_info=True)


async def handle_help() -> JSONResponse:
    """
    Handle /sline help command.
    
    Returns:
        JSONResponse: Help message
    """
    return JSONResponse(content={
        "response_type": "ephemeral",
        "text": """🤖 **Hey! I'm Sline, your AI coding teammate!**

**💬 How to Chat with Me:**

**Option 1: @mention** (Recommended)
Just @mention me in any message or thread! I'll join the conversation naturally.
• `@sline what files are in this project?`
• `@sline can you explain how the auth system works?`

**Option 2: /sline slash command**
Use `/sline` followed by your prompt - I'll respond in a thread!
• `/sline search for TODO comments`
• `/sline what's the project structure?`

**⚙️ Utility Commands:**
• `/sline status` - Show active conversations
• `/sline help` - Show this help message

**💡 Tip:** I'm conversational, not transactional! Feel free to ask questions, discuss approaches, and collaborate with your team.

**🚀 Future:** Custom commands coming soon! You'll be able to create shortcuts for common workflows via the dashboard.
"""
    })


async def handle_status(command_data: SlackCommandSchema) -> JSONResponse:
    """
    Handle /sline status command.
    
    Shows active conversations in the current channel.
    
    Args:
        command_data: Command data from Slack
        
    Returns:
        JSONResponse: Status information
    """
    # TODO: Query active conversations from database
    # For now, return placeholder
    return JSONResponse(content={
        "response_type": "ephemeral",
        "text": f"📊 Sline Status in <#{command_data.channel_id}>\n\n"
                "No active conversations found.\n\n"
                "💡 Start a conversation by @mentioning me or using `/sline <your prompt>`"
    })
