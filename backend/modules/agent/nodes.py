"""
LangGraph Workflow Nodes

Contains the node functions for the Sline workflow graph.
Each node calls SlineBrain with mode-specific instructions.
"""

from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from utils.logging import get_logger
from .state import SlineState
from .prompts import get_system_prompt
from .brain import create_sline_brain

logger = get_logger("agent.nodes")

# Cache for SlineBrain instances per workspace
_brain_cache: Dict[str, Any] = {}


def get_or_create_brain(workspace_path: str, include_write_tools: bool = False):
    """
    Get or create a SlineBrain for the given workspace.
    
    Caches brain instances to avoid recreating tools for each message.
    
    Args:
        workspace_path: Path to the workspace
        include_write_tools: Whether to include write tools
    
    Returns:
        SlineBrain agent instance
    """
    cache_key = f"{workspace_path}:{include_write_tools}"
    
    if cache_key not in _brain_cache:
        _brain_cache[cache_key] = create_sline_brain(
            workspace_path, 
            include_write_tools=include_write_tools
        )
    
    return _brain_cache[cache_key]


async def chat_node(state: SlineState) -> dict:
    """
    Handle normal chat: questions, explanations, light suggestions.
    
    This is the primary node for MVP - handles all conversational interactions
    with the codebase. Uses SlineBrain with read-only tools.
    
    Args:
        state: Current SlineState
    
    Returns:
        Dict with updated messages and mode
    """
    workspace_path = state["workspace_path"]
    mode = state.get("mode", "chat")
    
    logger.info(f"chat_node invoked for workspace: {workspace_path}")
    
    # Get or create brain with read-only tools
    brain = get_or_create_brain(workspace_path, include_write_tools=False)
    
    # Build messages with system prompt
    system_prompt = get_system_prompt(mode)
    
    # Prepare messages for the brain
    # The brain expects a dict with "messages" key
    messages = [SystemMessage(content=system_prompt)]
    messages.extend(state["messages"])
    
    try:
        # Invoke the brain (ReAct agent will handle tool calls automatically)
        result = await brain.ainvoke({"messages": messages})
        
        # Extract the AI's response
        # The result contains all messages including tool calls and responses
        response_messages = result.get("messages", [])
        
        # Find the final AI message (last AIMessage that's not a tool call)
        ai_response = None
        for msg in reversed(response_messages):
            if isinstance(msg, AIMessage) and not getattr(msg, 'tool_calls', None):
                ai_response = msg
                break
        
        if ai_response:
            logger.info(f"chat_node response: {ai_response.content[:100]}...")
            
            # Return only the new AI message to be added via add_messages reducer
            return {
                "messages": [ai_response],
                "mode": "chat",
            }
        else:
            # Fallback if no clear response
            logger.warning("No AI response found in brain output")
            return {
                "messages": [AIMessage(content="Hmm, Sline ran into an issue processing that. Could you try rephrasing?")],
                "mode": "chat",
            }
            
    except Exception as e:
        logger.error(f"Error in chat_node: {e}", exc_info=True)
        return {
            "messages": [AIMessage(content=f"Oops! Sline encountered an error: {str(e)}. Let me try again - could you rephrase that?")],
            "mode": "error",
            "error": str(e),
        }


async def plan_node(state: SlineState) -> dict:
    """
    Generate implementation plan using SlineBrain.
    
    Called when user requests a plan (e.g., "@sline create impl plan").
    Analyzes the codebase and creates a detailed, actionable plan.
    
    Args:
        state: Current SlineState
    
    Returns:
        Dict with updated messages, plan text, and mode="awaiting_approval"
    """
    workspace_path = state["workspace_path"]
    
    logger.info(f"plan_node invoked for workspace: {workspace_path}")
    
    # Get brain with read-only tools (planning doesn't need write tools)
    brain = get_or_create_brain(workspace_path, include_write_tools=False)
    
    # Build messages with planning mode instructions
    system_prompt = get_system_prompt("planning")
    
    messages = [SystemMessage(content=system_prompt)]
    messages.extend(state["messages"])
    
    try:
        result = await brain.ainvoke({"messages": messages})
        
        response_messages = result.get("messages", [])
        
        # Find the final AI message with the plan
        ai_response = None
        for msg in reversed(response_messages):
            if isinstance(msg, AIMessage) and not getattr(msg, 'tool_calls', None):
                ai_response = msg
                break
        
        if ai_response:
            plan_text = ai_response.content
            logger.info(f"plan_node generated plan: {plan_text[:100]}...")
            
            return {
                "messages": [ai_response],
                "mode": "awaiting_approval",
                "plan": plan_text,
            }
        else:
            return {
                "messages": [AIMessage(content="Sline couldn't generate a plan. Could you provide more details about what you'd like to accomplish?")],
                "mode": "chat",
            }
            
    except Exception as e:
        logger.error(f"Error in plan_node: {e}", exc_info=True)
        return {
            "messages": [AIMessage(content=f"Oops! Sline couldn't create the plan: {str(e)}")],
            "mode": "error",
            "error": str(e),
        }


async def execute_node(state: SlineState) -> dict:
    """
    Execute approved plan using SlineBrain with write tools.
    
    Called after user approves a plan. Uses SlineBrain with write_to_file
    tool enabled to make the changes described in the plan.
    
    Args:
        state: Current SlineState (must have plan and mode="approved")
    
    Returns:
        Dict with updated messages and mode="completed" or "error"
    """
    workspace_path = state["workspace_path"]
    plan = state.get("plan", "")
    
    logger.info(f"execute_node invoked for workspace: {workspace_path}")
    
    if not plan:
        return {
            "messages": [AIMessage(content="No plan to execute! Let's create one first.")],
            "mode": "chat",
        }
    
    # Get brain WITH write tools for execution
    brain = get_or_create_brain(workspace_path, include_write_tools=True)
    
    # Build messages with execute mode instructions
    system_prompt = get_system_prompt("executing")
    
    # Add context about the approved plan
    execution_context = f"\n\n## Approved Plan to Execute:\n{plan}\n\nNow execute this plan step by step."
    
    messages = [SystemMessage(content=system_prompt + execution_context)]
    messages.extend(state["messages"])
    
    try:
        result = await brain.ainvoke({"messages": messages})
        
        response_messages = result.get("messages", [])
        
        ai_response = None
        for msg in reversed(response_messages):
            if isinstance(msg, AIMessage) and not getattr(msg, 'tool_calls', None):
                ai_response = msg
                break
        
        if ai_response:
            logger.info(f"execute_node completed: {ai_response.content[:100]}...")
            
            return {
                "messages": [ai_response],
                "mode": "completed",
                "plan": None,  # Clear plan after execution
            }
        else:
            return {
                "messages": [AIMessage(content="Execution completed but Sline couldn't summarize the results.")],
                "mode": "completed",
            }
            
    except Exception as e:
        logger.error(f"Error in execute_node: {e}", exc_info=True)
        return {
            "messages": [AIMessage(content=f"❌ Error during execution: {str(e)}\n\nThe plan was not fully completed.")],
            "mode": "error",
            "error": str(e),
        }


def route_from_chat(state: SlineState) -> str:
    """
    Conditional edge: decide if we stay in chat or go to planning.
    
    Examines the last user message for intent keywords that suggest
    the user wants to create an implementation plan.
    
    Args:
        state: Current SlineState
    
    Returns:
        "plan" if user wants planning, "end" to stay in chat
    """
    messages = state.get("messages", [])
    
    if not messages:
        return "end"
    
    # Look at the last user message
    last_message = messages[-1]
    
    # Only check HumanMessages
    if not isinstance(last_message, HumanMessage):
        return "end"
    
    content = last_message.content.lower()
    
    # Keywords that trigger planning mode
    plan_triggers = [
        "create impl plan",
        "create implementation plan",
        "create a plan",
        "make a plan",
        "impl plan",
        "implementation plan",
        "plan this out",
        "let's plan",
    ]
    
    for trigger in plan_triggers:
        if trigger in content:
            logger.info(f"Plan trigger detected: '{trigger}'")
            return "plan"
    
    return "end"


def clear_brain_cache():
    """Clear the brain cache (useful for testing or config changes)."""
    global _brain_cache
    _brain_cache = {}
    logger.info("Brain cache cleared")
