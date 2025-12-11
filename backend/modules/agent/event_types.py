"""
LangChain Event Type Constants

Type-safe enum for astream_events() event types.
Based on LangChain's streaming event API.

Using StrEnum provides:
- Type safety and autocomplete
- String-like behavior (can compare directly with strings)
- Enum introspection and validation
"""

from enum import StrEnum


class LangChainEventType(StrEnum):
    """
    Event types emitted by LangGraph's astream_events() method.
    
    These events allow real-time monitoring of agent execution,
    including LLM calls, tool invocations, and chain execution.
    """
    
    # Chat model events
    CHAT_MODEL_START = "on_chat_model_start"
    CHAT_MODEL_STREAM = "on_chat_model_stream"
    CHAT_MODEL_END = "on_chat_model_end"
    
    # Tool events
    TOOL_START = "on_tool_start"
    TOOL_END = "on_tool_end"
    
    # Chain/Graph events
    CHAIN_START = "on_chain_start"
    CHAIN_END = "on_chain_end"
    
    # Retriever events
    RETRIEVER_START = "on_retriever_start"
    RETRIEVER_END = "on_retriever_end"
    
    # Prompt events
    PROMPT_START = "on_prompt_start"
    PROMPT_END = "on_prompt_end"
