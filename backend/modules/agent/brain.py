"""
SlineBrain - ReAct Agent Creation

Creates the SlineBrain agent using LangGraph's create_react_agent.
The brain is created per-conversation since tools are bound to workspace_path.
"""

from typing import Optional
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from config import settings
from utils.logging import get_logger
from .tools.factory import make_bound_tools, make_write_tools
from .prompts import get_system_prompt

logger = get_logger("agent.brain")

# Cache the LLM model instance (same model for all conversations)
_llm_model = None


def get_llm_model():
    """
    Get LLM model based on config (singleton).
    
    Uses CLINE_PROVIDER, CLINE_API_KEY, CLINE_MODEL_ID from config.
    These will be renamed to SLINE_* in the future.
    
    Returns:
        ChatModel instance (ChatAnthropic or ChatOpenAI)
    
    Raises:
        ValueError: If provider is not supported or API key is missing
    """
    global _llm_model
    
    if _llm_model is not None:
        return _llm_model
    
    provider = settings.cline_provider
    api_key = settings.cline_api_key
    model_id = settings.cline_model_id
    
    if not api_key:
        raise ValueError(
            "CLINE_API_KEY is not configured. "
            "Set it in backend/.env or via the Settings page."
        )
    
    if not model_id:
        raise ValueError(
            "CLINE_MODEL_ID is not configured. "
            "Set it in backend/.env or via the Settings page."
        )
    
    logger.info(f"Initializing LLM model: provider={provider}, model={model_id}")
    
    if provider == "anthropic":
        _llm_model = ChatAnthropic(
            model=model_id,
            api_key=api_key,
            max_tokens=4096,
        )
    elif provider in ("openai-native", "openai"):
        _llm_model = ChatOpenAI(
            model=model_id,
            api_key=api_key,
        )
    elif provider == "openrouter":
        # OpenRouter uses OpenAI-compatible API
        _llm_model = ChatOpenAI(
            model=model_id,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
    elif provider == "openai-compatible":
        # Custom OpenAI-compatible endpoint
        base_url = getattr(settings, 'cline_base_url', None)
        if not base_url:
            raise ValueError(
                "CLINE_BASE_URL is required for openai-compatible provider"
            )
        _llm_model = ChatOpenAI(
            model=model_id,
            api_key=api_key,
            base_url=base_url,
        )
    else:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported: anthropic, openai-native, openai, openrouter, openai-compatible"
        )
    
    return _llm_model


def create_sline_brain(workspace_path: str, include_write_tools: bool = False):
    """
    Create SlineBrain ReAct agent with tools bound to workspace.
    
    This is called ONCE per conversation (since workspace_path varies per project).
    The resulting agent handles multi-step tool use via ReAct pattern.
    
    Args:
        workspace_path: Absolute path to cloned repo workspace
        include_write_tools: If True, include write_to_file tool (Phase 2)
    
    Returns:
        CompiledGraph: LangGraph ReAct agent ready for ainvoke()
    """
    model = get_llm_model()
    
    # Create tools with workspace bound
    tools = make_bound_tools(workspace_path)
    
    # Add write tools if requested (for execute mode)
    if include_write_tools:
        tools.extend(make_write_tools(workspace_path))
    
    logger.info(
        f"Creating SlineBrain for workspace: {workspace_path}, "
        f"tools: {[t.name for t in tools]}"
    )
    
    # Create ReAct agent
    # Note: System prompt is passed per-invocation via messages for flexibility
    agent = create_react_agent(
        model=model,
        tools=tools,
    )
    
    return agent


def reset_llm_model():
    """
    Reset the cached LLM model.
    
    Call this after changing API keys or provider settings
    to force re-initialization on next use.
    """
    global _llm_model
    _llm_model = None
    logger.info("LLM model cache cleared")
