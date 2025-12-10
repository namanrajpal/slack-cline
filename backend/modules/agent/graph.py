"""
LangGraph Workflow Definition

Defines the Sline workflow graph that orchestrates chat, planning, and execution.
For MVP, we use a simplified graph with just chat_node.
"""

from langgraph.graph import StateGraph, END

from utils.logging import get_logger
from .state import SlineState
from .nodes import chat_node, plan_node, execute_node, route_from_chat

logger = get_logger("agent.graph")


def create_sline_graph():
    """
    Create and compile the Sline workflow graph.
    
    MVP Graph (Phase 1):
        START -> chat_node -> END
    
    Full Graph (Phase 2):
        START -> chat_node -> [conditional: plan or end]
                    |
                    v
               plan_node -> awaiting_approval
                    |
                    v (on approval)
               execute_node -> END
    
    Returns:
        CompiledStateGraph ready for .ainvoke() or .astream()
    """
    # Create the graph with our state schema
    graph = StateGraph(SlineState)
    
    # Add nodes
    graph.add_node("chat", chat_node)
    graph.add_node("plan", plan_node)
    graph.add_node("execute", execute_node)
    
    # Set entry point
    graph.set_entry_point("chat")
    
    # Add edges
    # From chat: either go to plan or end
    graph.add_conditional_edges(
        "chat",
        route_from_chat,
        {
            "plan": "plan",
            "end": END,
        }
    )
    
    # From plan: go to end (approval handled separately)
    graph.add_edge("plan", END)
    
    # From execute: go to end
    graph.add_edge("execute", END)
    
    # Compile the graph
    compiled = graph.compile()
    
    logger.info("Sline graph compiled successfully")
    
    return compiled


def create_simple_chat_graph():
    """
    Create a minimal chat-only graph for MVP.
    
    This is the simplest possible graph:
        START -> chat_node -> END
    
    No conditional routing, no planning, no execution.
    Just pure chat with file tools.
    
    Returns:
        CompiledStateGraph for chat-only interactions
    """
    graph = StateGraph(SlineState)
    
    # Single node
    graph.add_node("chat", chat_node)
    
    # Entry and exit
    graph.set_entry_point("chat")
    graph.add_edge("chat", END)
    
    compiled = graph.compile()
    
    logger.info("Simple chat graph compiled")
    
    return compiled


# Create the default graph instance
# For MVP, use the simple chat graph
# Switch to create_sline_graph() when planning/execute is ready
_default_graph = None


def get_graph():
    """
    Get the default compiled graph instance.
    
    Lazily creates the graph on first call.
    
    Returns:
        CompiledStateGraph
    """
    global _default_graph
    
    if _default_graph is None:
        # For MVP, use simple chat graph
        # TODO: Switch to create_sline_graph() in Phase 2
        _default_graph = create_simple_chat_graph()
    
    return _default_graph


def reset_graph():
    """Reset the graph instance (useful for testing)."""
    global _default_graph
    _default_graph = None
    logger.info("Graph instance reset")
