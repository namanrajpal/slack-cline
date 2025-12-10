"""
Project Classifier

Uses LLM to intelligently determine which project the user is asking about
based on their question and the available project descriptions.
"""

from typing import List
from langchain_core.messages import SystemMessage, HumanMessage

from utils.logging import get_logger
from models.project import ProjectModel

logger = get_logger("agent.classifier")


async def classify_project(
    user_question: str,
    projects: List[ProjectModel],
    llm_model
) -> ProjectModel:
    """
    Determine which project the user is asking about.
    
    MVP: Returns first project by default.
    
    TODO: Implement smarter classification:
    - Load project context (README, file structure)
    - Reason over which project fits the question best
    - Ask user to clarify if uncertain
    - Handle multi-project queries
    
    Args:
        user_question: The user's question/prompt
        projects: List of available ProjectModel instances
        llm_model: The LLM model instance (unused in MVP)
    
    Returns:
        The selected ProjectModel
    """
    if not projects:
        raise ValueError("No projects available for classification")
    
    # MVP: Just use first project
    # This keeps the architecture ready for smart classification later
    selected_project = projects[0]
    
    logger.info(f"Using first project by default: {selected_project.name}")
    
    return selected_project


async def list_all_projects_tool(projects: List[ProjectModel]) -> str:
    """
    Format all available projects as a tool response.
    
    This can be used as a tool for the agent to discover what projects
    Sline knows about.
    
    Args:
        projects: List of ProjectModel instances
    
    Returns:
        Formatted string listing all projects
    """
    if not projects:
        return "No projects are currently configured."
    
    lines = ["**Available Projects:**\n"]
    for project in projects:
        desc = project.description or "No description"
        lines.append(f"• **{project.name}**: {desc}")
        lines.append(f"  Repository: {project.repo_url}")
    
    return "\n".join(lines)
