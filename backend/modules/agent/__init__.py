"""
Sline Agent Module

This module contains the SlineBrain agent implementation using LangGraph.
It provides a conversational AI coding assistant for Slack integration.

Key Components:
- SlineState: TypedDict for workflow state
- SlineBrain: ReAct agent with file tools
- AgentService: Service layer for Slack gateway integration
"""

from .state import SlineState
from .brain import create_sline_brain, get_llm_model
from .service import AgentService, get_agent_service

__all__ = [
    "SlineState",
    "create_sline_brain",
    "get_llm_model",
    "AgentService",
    "get_agent_service",
]
