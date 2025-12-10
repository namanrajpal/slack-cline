"""
Agent Service

Main service layer for Sline agent, called by Slack gateway.
Handles conversation state management and graph invocation.
"""

import json
import os
from typing import Optional, AsyncIterator
from uuid import UUID

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from utils.logging import get_logger
from models.project import ProjectModel
from models.conversation import ConversationModel
from .state import SlineState, create_initial_state
from .graph import get_graph

logger = get_logger("agent.service")

# Singleton service instance
_agent_service: Optional["AgentService"] = None


class AgentService:
    """
    Service layer for Sline agent.
    
    Responsibilities:
    - Load/save conversation state (in-memory for MVP, DB later)
    - Resolve project → workspace mapping
    - Invoke LangGraph workflow
    - Translate between Slack messages and agent state
    """
    
    def __init__(self):
        """Initialize the agent service."""
        # In-memory conversation state cache for MVP
        # Key: f"{channel_id}:{thread_ts}"
        self._conversations: dict[str, SlineState] = {}
        
        # Workspace base path - /data is mounted as Docker volume for persistence
        self._workspace_base = "/data/workspaces"
        os.makedirs(self._workspace_base, exist_ok=True)
        
        logger.info(f"AgentService initialized, workspace base: {self._workspace_base}")
    
    async def handle_message(
        self,
        channel_id: str,
        thread_ts: str,
        user_id: str,
        text: str,
        session: AsyncSession,
    ) -> str:
        """
        Handle incoming Slack message.
        
        This is the main entry point for processing user messages.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Slack thread timestamp (conversation ID)
            user_id: Slack user ID who sent the message
            text: Message text
            session: Database session
        
        Returns:
            AI response text to post back to Slack
        """
        conversation_key = f"{channel_id}:{thread_ts}"
        
        logger.info(f"Handling message for {conversation_key}: {text[:50]}...")
        
        # Get or create conversation state (pass text for project classification)
        state = await self._get_or_create_state(
            channel_id=channel_id,
            thread_ts=thread_ts,
            user_id=user_id,
            session=session,
            user_question=text,  # Pass question for LLM classification
        )
        
        if state is None:
            return "❌ Sline couldn't find any configured projects. Please add projects first."
        
        # Add the user message to state
        user_message = HumanMessage(content=text)
        state["messages"].append(user_message)
        state["user_id"] = user_id
        
        # Get the graph
        graph = get_graph()
        
        try:
            # Invoke the graph
            result = await graph.ainvoke(state)
            
            # Update cached state
            self._conversations[conversation_key] = result
            
            # Save state to database
            await self._save_state(
                channel_id=channel_id,
                thread_ts=thread_ts,
                user_id=user_id,
                state=result,
                session=session,
            )
            
            # Extract the AI response
            ai_response = self._extract_ai_response(result)
            
            logger.info(f"Response for {conversation_key}: {ai_response[:100]}...")
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return f"❌ Sline encountered an error: {str(e)}"
    
    async def handle_approval(
        self,
        channel_id: str,
        thread_ts: str,
        approved: bool,
        user_id: str,
        session: AsyncSession,
    ) -> str:
        """
        Handle plan approval/rejection from Slack button click.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Slack thread timestamp
            approved: True if approved, False if rejected
            user_id: User who clicked the button
            session: Database session
        
        Returns:
            Response text
        """
        conversation_key = f"{channel_id}:{thread_ts}"
        
        state = self._conversations.get(conversation_key)
        
        if not state:
            return "❌ Couldn't find the conversation. The plan may have expired."
        
        if state.get("mode") != "awaiting_approval":
            return "❌ No plan is awaiting approval."
        
        if not approved:
            # User rejected the plan
            state["mode"] = "chat"
            state["plan"] = None
            self._conversations[conversation_key] = state
            return "👍 Plan cancelled. What would you like to do instead?"
        
        # User approved - trigger execute_node
        # For Phase 2, this would invoke the execute_node
        # For now, just acknowledge
        state["mode"] = "executing"
        
        # TODO: Invoke execute_node in Phase 2
        # For now, just return acknowledgment
        return "🚀 Plan approved! Execution is coming in Phase 2. For now, Sline can help you with code questions."
    
    async def _get_or_create_state(
        self,
        channel_id: str,
        thread_ts: str,
        user_id: str,
        session: AsyncSession,
        user_question: str = "",
    ) -> Optional[SlineState]:
        """
        Get existing conversation state or create new one.
        
        Uses LLM-based project classification to determine which project
        the user is asking about.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Slack thread timestamp
            user_id: Slack user ID
            session: Database session
            user_question: The user's question (for project classification)
        
        Returns:
            SlineState or None if no projects available
        """
        conversation_key = f"{channel_id}:{thread_ts}"
        
        # Check cache first
        if conversation_key in self._conversations:
            return self._conversations[conversation_key]
        
        # Try to load from database
        result = await session.execute(
            select(ConversationModel).filter(
                ConversationModel.channel_id == channel_id,
                ConversationModel.thread_ts == thread_ts,
            )
        )
        conversation = result.scalar_one_or_none()
        
        if conversation and conversation.state_json:
            # Load existing conversation state from database
            state = self.json_to_state(conversation.state_json)
            self._conversations[conversation_key] = state
            logger.info(f"Loaded existing conversation {conversation_key} from database")
            return state
        
        # No existing conversation - create new one
        # Get all projects for classification
        all_projects = await self._get_all_projects(session)
        
        if not all_projects:
            logger.warning("No projects configured in the system")
            return None
        
        # Use LLM classifier to select the relevant project
        from .classifier import classify_project
        from .brain import get_llm_model
        
        project = await classify_project(
            user_question=user_question,
            projects=all_projects,
            llm_model=get_llm_model()
        )
        
        logger.info(f"Selected project '{project.name}' for conversation {conversation_key}")
        
        # Get or create workspace
        workspace_path = await self._get_workspace_path(project)
        
        # Create initial state
        state = create_initial_state(
            workspace_path=workspace_path,
            project_id=str(project.id),
            channel_id=channel_id,
            thread_ts=thread_ts,
            user_id=user_id,
        )
        
        # Cache it
        self._conversations[conversation_key] = state
        
        logger.info(f"Created new conversation state for {conversation_key} using project {project.name}")
        
        return state
    
    async def _get_all_projects(
        self,
        session: AsyncSession,
    ) -> list[ProjectModel]:
        """
        Get all available projects.
        
        Args:
            session: Database session
        
        Returns:
            List of ProjectModel instances
        """
        result = await session.execute(select(ProjectModel))
        return list(result.scalars().all())
    
    async def _get_workspace_path(self, project: ProjectModel) -> str:
        """
        Get the workspace path for a project.
        
        For MVP, we use the repo URL to create a simple workspace.
        In production, this would clone the repo.
        
        Args:
            project: Project model
        
        Returns:
            Absolute path to workspace
        """
        # Create a workspace directory based on project ID
        workspace_path = os.path.join(self._workspace_base, str(project.id))
        
        # For MVP, just create the directory if it doesn't exist
        # In production, this would clone the repo
        if not os.path.exists(workspace_path):
            os.makedirs(workspace_path)
            
            # Create a placeholder README
            readme_path = os.path.join(workspace_path, "README.md")
            with open(readme_path, "w") as f:
                f.write(f"# Workspace for {project.repo_url}\n\n")
                f.write("This is a placeholder workspace.\n")
                f.write("In production, this directory would contain the cloned repository.\n")
            
            logger.info(f"Created workspace at {workspace_path}")
        
        return workspace_path
    
    async def _save_state(
        self,
        channel_id: str,
        thread_ts: str,
        user_id: str,
        state: SlineState,
        session: AsyncSession,
    ) -> None:
        """
        Save conversation state to database.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Slack thread timestamp
            user_id: Slack user ID
            state: SlineState to save
            session: Database session
        """
        try:
            # Check if conversation exists
            result = await session.execute(
                select(ConversationModel).filter(
                    ConversationModel.channel_id == channel_id,
                    ConversationModel.thread_ts == thread_ts,
                )
            )
            conversation = result.scalar_one_or_none()
            
            # Serialize state
            state_json = self.state_to_json(state)
            
            if conversation:
                # Update existing conversation
                conversation.state_json = state_json
                conversation.update_metadata(user_id)
                logger.debug(f"Updated conversation {channel_id}:{thread_ts} in database")
            else:
                # Create new conversation
                conversation = ConversationModel(
                    channel_id=channel_id,
                    thread_ts=thread_ts,
                    project_id=UUID(state["project_id"]),
                    state_json=state_json,
                    last_user_id=user_id,
                    message_count=len(state.get("messages", [])),
                )
                session.add(conversation)
                logger.info(f"Created new conversation {channel_id}:{thread_ts} in database")
            
            # Commit changes
            await session.commit()
            
        except Exception as e:
            logger.error(f"Error saving conversation state: {e}", exc_info=True)
            # Don't raise - we still have in-memory cache
            await session.rollback()
    
    def _extract_ai_response(self, state: SlineState) -> str:
        """
        Extract the AI response text from state.
        
        Args:
            state: SlineState after graph execution
        
        Returns:
            Response text string
        """
        messages = state.get("messages", [])
        
        # Find the last AI message
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                return msg.content
        
        return "Sline processed your message but didn't generate a response."
    
    def state_to_json(self, state: SlineState) -> dict:
        """
        Serialize SlineState to JSON for database storage.
        
        Args:
            state: SlineState to serialize
        
        Returns:
            JSON-serializable dict
        """
        return {
            "workspace_path": state["workspace_path"],
            "project_id": state["project_id"],
            "channel_id": state["channel_id"],
            "thread_ts": state["thread_ts"],
            "user_id": state["user_id"],
            "mode": state["mode"],
            "plan": state.get("plan"),
            "error": state.get("error"),
            "files_context": state.get("files_context"),
            "messages": [
                {
                    "type": msg.__class__.__name__,
                    "content": msg.content,
                }
                for msg in state.get("messages", [])
            ],
        }
    
    def json_to_state(self, json_data: dict) -> SlineState:
        """
        Deserialize JSON from database to SlineState.
        
        Args:
            json_data: JSON dict from database
        
        Returns:
            SlineState
        """
        # Reconstruct messages
        messages = []
        for msg_data in json_data.get("messages", []):
            msg_type = msg_data.get("type")
            content = msg_data.get("content", "")
            
            if msg_type == "HumanMessage":
                messages.append(HumanMessage(content=content))
            elif msg_type == "AIMessage":
                messages.append(AIMessage(content=content))
        
        return SlineState(
            messages=messages,
            workspace_path=json_data.get("workspace_path", ""),
            project_id=json_data.get("project_id", ""),
            channel_id=json_data.get("channel_id", ""),
            thread_ts=json_data.get("thread_ts", ""),
            user_id=json_data.get("user_id", ""),
            mode=json_data.get("mode", "chat"),
            plan=json_data.get("plan"),
            error=json_data.get("error"),
            files_context=json_data.get("files_context"),
        )


def get_agent_service() -> AgentService:
    """
    Get the singleton AgentService instance.
    
    Returns:
        AgentService instance
    """
    global _agent_service
    
    if _agent_service is None:
        _agent_service = AgentService()
    
    return _agent_service


def reset_agent_service():
    """Reset the agent service (useful for testing)."""
    global _agent_service
    _agent_service = None
    logger.info("Agent service reset")
