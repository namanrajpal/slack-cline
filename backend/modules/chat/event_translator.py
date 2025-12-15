"""
LangChain to AG-UI event translator.

Translates LangGraph's astream_events() output to AG-UI protocol events
that CopilotKit can consume.
"""

from typing import Optional, AsyncIterator
from uuid import uuid4

from modules.agent.state import SlineState
from modules.agent.event_types import LangChainEventType
from schemas.agui import (
    AGUIEvent,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    StepStartedEvent,
    StepFinishedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallEndEvent,
    generate_message_id,
    generate_tool_call_id,
    generate_step_id,
)
from utils.logging import get_logger

logger = get_logger("chat.event_translator")


class EventTranslatorState:
    """
    Tracks state during event translation for stable ID generation.
    """
    def __init__(self, run_id: str, message_id: str):
        self.run_id = run_id
        self.message_id = message_id
        self.tool_counter = 0
        self.step_counter = 0
        self.active_tools: dict[str, str] = {}  # langchain_id -> tool_call_id
        self.active_steps: dict[str, str] = {}  # langchain_id -> step_id
        self.message_started = False


def translate_langchain_event(
    event: dict,
    translator_state: EventTranslatorState,
) -> Optional[AGUIEvent]:
    """
    Translate a single LangChain astream_events() output to AG-UI format.
    
    Args:
        event: LangChain event dict with keys: event, name, data, tags, etc.
        translator_state: Translator state for ID tracking
        
    Returns:
        AGUIEvent or None if event should be skipped
    """
    event_type = event.get("event")
    event_name = event.get("name", "")
    event_data = event.get("data", {})
    
    # Chat model streaming (token by token)
    if event_type == LangChainEventType.CHAT_MODEL_STREAM:
        chunk = event_data.get("chunk")
        raw_content = chunk.content if chunk and hasattr(chunk, "content") else ""

        # Normalize provider-specific chunk shapes (e.g., Anthropic content blocks)
        if isinstance(raw_content, str):
            content = raw_content
        elif isinstance(raw_content, list):
            # Anthropic-style blocks: [{"type":"text","text":"..."}, ...]
            parts: list[str] = []
            for block in raw_content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        parts.append(block.get("text", ""))
                else:
                    parts.append(str(block))
            content = "".join(parts)
        else:
            content = str(raw_content)
        
        if content:
            # Start message if not started yet
            if not translator_state.message_started:
                translator_state.message_started = True
                return TextMessageStartEvent(
                    message_id=translator_state.message_id,
                    role="assistant"
                )
            
            # Stream content delta
            return TextMessageContentEvent(
                message_id=translator_state.message_id,
                delta=content
            )
    
    # Chat model start
    elif event_type == LangChainEventType.CHAT_MODEL_START:
        if not translator_state.message_started:
            translator_state.message_started = True
            return TextMessageStartEvent(
                message_id=translator_state.message_id,
                role="assistant"
            )
    
    # Chat model end
    # NOTE: Don't send textMessageEnd here! In a ReAct agent, there are multiple
    # LLM calls (one per reasoning step). Sending textMessageEnd on each CHAT_MODEL_END
    # would prematurely close the message. The textMessageEnd is sent at the very end
    # of graph execution in stream_agui_events() instead.
    elif event_type == LangChainEventType.CHAT_MODEL_END:
        # Do nothing - let stream_agui_events handle the final textMessageEnd
        pass
    
    # Tool start
    elif event_type == LangChainEventType.TOOL_START:
        tool_name = event_name
        
        # Generate stable tool call ID
        tool_call_id = generate_tool_call_id(
            translator_state.run_id,
            translator_state.tool_counter
        )
        translator_state.tool_counter += 1
        
        # Track this tool
        run_id_from_event = event.get("run_id", "")
        if run_id_from_event:
            translator_state.active_tools[run_id_from_event] = tool_call_id
        
        return ToolCallStartEvent(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            parent_message_id=translator_state.message_id
        )
    
    # Tool end
    elif event_type == LangChainEventType.TOOL_END:
        run_id_from_event = event.get("run_id", "")
        tool_call_id = translator_state.active_tools.get(run_id_from_event)
        
        if tool_call_id:
            output = event_data.get("output", {})
            result_str = str(output) if output else None
            
            return ToolCallEndEvent(
                tool_call_id=tool_call_id,
                result=result_str
            )
    
    # Chain/step start (for grouping tool calls)
    elif event_type == LangChainEventType.CHAIN_START:
        # Only create steps for meaningful chains (not internal ones)
        if event_name and not event_name.startswith("RunnableSequence"):
            step_id = generate_step_id(
                translator_state.run_id,
                translator_state.step_counter
            )
            translator_state.step_counter += 1
            
            run_id_from_event = event.get("run_id", "")
            if run_id_from_event:
                translator_state.active_steps[run_id_from_event] = step_id
            
            return StepStartedEvent(
                step_id=step_id,
                step_name=event_name
            )
    
    # Chain/step end
    elif event_type == LangChainEventType.CHAIN_END:
        run_id_from_event = event.get("run_id", "")
        step_id = translator_state.active_steps.get(run_id_from_event)
        
        if step_id:
            return StepFinishedEvent(
                step_id=step_id
            )
    
    # Skip other events
    return None


async def stream_agui_events(
    graph,
    state: SlineState,
    thread_id: str,
    run_id: str,
    message_index: int,
) -> AsyncIterator[AGUIEvent]:
    """
    Stream AG-UI events from LangGraph execution.
    
    Wraps graph.astream_events() and translates to AG-UI.
    Emits runStarted at beginning, runFinished/runError at end.
    
    Args:
        graph: LangGraph compiled graph
        state: SlineState to execute
        thread_id: Conversation thread ID
        run_id: Unique run ID for this execution
        message_index: Message index for stable ID generation
        
    Yields:
        AGUIEvent instances ready for SSE streaming
    """
    # Generate stable message ID
    message_id = generate_message_id(thread_id, message_index)
    
    # Initialize translator state
    translator_state = EventTranslatorState(
        run_id=run_id,
        message_id=message_id
    )
    
    # Emit run started
    yield RunStartedEvent(
        thread_id=thread_id,
        run_id=run_id
    )
    
    try:
        # Stream events from LangGraph
        async for event in graph.astream_events(state, version="v2"):
            # Translate to AG-UI
            agui_event = translate_langchain_event(event, translator_state)
            
            if agui_event:
                yield agui_event
        
        # Ensure message end if started
        if translator_state.message_started:
            yield TextMessageEndEvent(
                message_id=translator_state.message_id
            )
        
        # Emit run finished
        yield RunFinishedEvent(
            thread_id=thread_id,
            run_id=run_id
        )
        
    except Exception as e:
        logger.error(f"Error streaming AG-UI events: {e}", exc_info=True)
        
        # Emit run error
        yield RunErrorEvent(
            thread_id=thread_id,
            run_id=run_id,
            error=str(e)
        )
