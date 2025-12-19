"""
Chat routes for AG-UI-compatible streaming.

Implements:
- POST /api/chat - Streaming chat endpoint (SSE)
- GET /api/chat/thread/{thread_id} - Thread reload for conversation persistence
"""

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import StreamingResponse, JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database import get_session
from modules.agent.service import get_agent_service
from modules.chat.sse_utils import sse_generator
from schemas.agui import (
    ChatRequest,
    ChatThreadResponse,
    ChatMessage,
    generate_message_id,
)
from schemas.chat import ConversationSummary, ConversationListResponse
from models.conversation import ConversationModel
from utils.logging import get_logger

logger = get_logger("chat.routes")

router = APIRouter()


@router.get("/info")
async def chat_info():
    """
    Chat runtime info endpoint.
    
    Returns information about available agents.
    
    Returns:
        Runtime info with agents list
    """
    return {
        "agents": [
            {
                "name": "default",
                "description": "Sline AI coding assistant",
                "model": "sline-agent",
                "supportsVision": False,
                "supportsFunctionCalling": True,
            }
        ]
    }


@router.post("", response_model=None)
@router.post("/", response_model=None)
async def chat_endpoint(
    raw_request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Chat endpoint with AG-UI event streaming.
    
    Accepts chat requests, invokes agent, and streams AG-UI events back via SSE.
    
    Args:
        request: CopilotKit request with threadId, messages, etc.
        session: Database session
        
    Returns:
        StreamingResponse with SSE events (text/event-stream)
    """
    # Parse request body manually for debugging
    body = await raw_request.json()
    logger.info(f"Chat raw request body: {body}")
    
    # Try to parse as ChatRequest
    try:
        request = ChatRequest(**body)
    except Exception as e:
        logger.error(f"Failed to parse chat request: {e}")
        logger.error(f"Request body was: {body}")
        raise
    
    # Handle method-based routing
    if request.method == "info":
        # Return runtime info (same as GET /info)
        logger.info("Handling method=info request")
        return JSONResponse({
            "agents": [
                {
                    "name": "default",
                    "description": "Sline AI coding assistant",
                    "model": "sline-agent",
                    "supportsVision": False,
                    "supportsFunctionCalling": True,
                }
            ]
        })
    
    # Handle chat method
    logger.info(f"Chat request: threadId={request.thread_id}, message_count={len(request.messages) if request.messages else 0}")
    
    # Extract thread ID and last user message
    thread_id = request.thread_id or "default-thread"
    
    if not request.messages:
        logger.warning("No messages in chat request")
        return StreamingResponse(
            iter([]),
            media_type="text/event-stream"
        )
    
    # Get the last user message
    last_message = request.messages[-1]
    user_text = last_message.content
    user_id = "dashboard_user"  # Default for dashboard
    channel_id = "dashboard"  # Use "dashboard" as channel identifier
    
    logger.info(f"Chat request for thread {thread_id}: {user_text[:50]}...")
    
    # Get agent service
    agent_service = get_agent_service()
    
    # Stream AG-UI events from agent
    agui_events = agent_service.handle_message_streaming(
        channel_id=channel_id,
        thread_ts=thread_id,
        user_id=user_id,
        text=user_text,
        session=session,
    )
    
    # Convert to SSE strings
    sse_stream = sse_generator(agui_events)
    
    # Return streaming response
    return StreamingResponse(
        sse_stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/threads")
async def list_threads(
    limit: int = Query(default=50, le=100),
    session: AsyncSession = Depends(get_session),
) -> ConversationListResponse:
    """
    List recent chat threads for the dashboard.
    
    Returns conversations from the "dashboard" channel, ordered by most recent.
    
    Args:
        limit: Maximum number of threads to return (default 50, max 100)
        session: Database session
        
    Returns:
        ConversationListResponse with list of conversation summaries
    """
    logger.info(f"Listing threads (limit={limit})")
    
    # Query conversations for dashboard channel
    result = await session.execute(
        select(ConversationModel)
        .filter(ConversationModel.channel_id == "dashboard")
        .order_by(desc(ConversationModel.updated_at))
        .limit(limit)
    )
    conversations = result.scalars().all()
    
    # Convert to summaries
    summaries = []
    for conv in conversations:
        state_json = conv.state_json or {}
        messages = state_json.get("messages", [])
        
        # Use stored title, or fallback to extracting from messages
        title = conv.title or "New conversation"
        
        # Get last message preview
        last_preview = ""
        for msg in reversed(messages):
            content = msg.get("content", "")
            if content:
                last_preview = content[:100] + ("..." if len(content) > 100 else "")
                break
        
        summaries.append(
            ConversationSummary(
                thread_id=conv.thread_ts,
                channel_id=conv.channel_id,
                project_id=conv.project_id,
                updated_at=conv.updated_at,
                message_count=conv.message_count or len(messages),
                title=title,
                last_message_preview=last_preview,
            )
        )
    
    logger.info(f"Returning {len(summaries)} threads")
    return ConversationListResponse(conversations=summaries)


@router.get("/thread/{thread_id}")
async def get_thread(
    thread_id: str,
    session: AsyncSession = Depends(get_session),
) -> ChatThreadResponse:
    """
    Return persisted transcript for thread reload.
    
    Returns messages with stable messageIds that match what was streamed.
    
    Args:
        thread_id: Thread/conversation ID
        session: Database session
        
    Returns:
        CopilotKitThreadResponse with messages array
    """
    logger.info(f"Thread reload request for {thread_id}")
    
    # Load conversation from database
    result = await session.execute(
        select(ConversationModel).filter(
            ConversationModel.channel_id == "dashboard",
            ConversationModel.thread_ts == thread_id,
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        logger.warning(f"Thread {thread_id} not found")
        return ChatThreadResponse(
            thread_id=thread_id,
            messages=[],
            state=None
        )
    
    # Extract messages from state_json
    state_json = conversation.state_json
    messages_data = state_json.get("messages", [])
    
    # Convert to chat message format with stable IDs
    chat_messages = []
    user_index = 0
    ai_index = 0
    
    for msg_data in messages_data:
        msg_type = msg_data.get("type")
        content = msg_data.get("content", "")
        
        if msg_type == "HumanMessage":
            chat_messages.append(
                ChatMessage(
                    id=f"{thread_id}:user:{user_index}",
                    role="user",
                    content=content
                )
            )
            user_index += 1
        elif msg_type == "AIMessage":
            # Use same stable ID generation as streaming
            msg_id = generate_message_id(thread_id, ai_index)
            chat_messages.append(
                ChatMessage(
                    id=msg_id,
                    role="assistant",
                    content=content
                )
            )
            ai_index += 1
    
    logger.info(f"Returning {len(chat_messages)} messages for thread {thread_id}")
    
    return ChatThreadResponse(
        thread_id=thread_id,
        messages=chat_messages,
        state=None  # Optional: can include project context here later
    )
