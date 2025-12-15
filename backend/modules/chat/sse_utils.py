"""
Server-Sent Events (SSE) utilities for AG-UI event streaming.
"""

from typing import AsyncIterator
from schemas.agui import AGUIEvent


def encode_sse(event: AGUIEvent) -> str:
    """
    Encode AG-UI event as standard SSE frame.
    
    Format:
        data: {"type":"textMessageContent",...}\n\n
    
    Args:
        event: AG-UI event to encode
        
    Returns:
        SSE-formatted string with data: prefix and double newline
    """
    json_str = event.model_dump_json(by_alias=True, exclude_none=True)
    return f"data: {json_str}\n\n"


async def sse_generator(events: AsyncIterator[AGUIEvent]) -> AsyncIterator[str]:
    """
    Async generator that encodes AG-UI events to SSE strings.
    
    Args:
        events: Async iterator of AG-UI events
        
    Yields:
        SSE-formatted strings ready to stream to client
    """
    async for event in events:
        yield encode_sse(event)
