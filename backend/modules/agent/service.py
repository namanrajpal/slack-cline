"""
Agent Service

Main service layer for Sline agent, called by Slack gateway.
Handles conversation state management and graph invocation.
"""

import json
import os
from typing import Optional, AsyncIterator
from uuid import UUID, uuid4

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from utils.logging import get_logger
from models.project import ProjectModel
from models.conversation import ConversationModel
from .state import SlineState, create_initial_state
from .graph import get_graph
from .workspace_manager import get_workspace_manager, GitError

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
    
    async def handle_message_streaming(
        self,
        channel_id: str,
        thread_ts: str,
        user_id: str,
        text: str,
        session: AsyncSession,
        project_id: Optional[str] = None,
    ) -> AsyncIterator:
        """
        Handle incoming message with AG-UI event streaming.
        
        This method is used by CopilotKit/Dashboard for real-time streaming.
        Uses astream_events() instead of ainvoke() for token-by-token streaming.
        
        Args:
            channel_id: Channel ID (or "dashboard" for Dashboard)
            thread_ts: Thread timestamp (conversation ID / UUID)
            user_id: User ID
            text: Message text
            session: Database session
            project_id: Optional project ID (dashboard-specific context)
        
        Yields:
            AGUIEvent instances for SSE streaming
        """
        from modules.chat.event_translator import stream_agui_events
        from schemas.agui import RunErrorEvent
        
        conversation_key = f"{channel_id}:{thread_ts}"
        
        logger.info(f"Handling streaming message for {conversation_key}: {text[:50]}...")
        
        try:
            # Get or create conversation state
            state = await self._get_or_create_state(
                channel_id=channel_id,
                thread_ts=thread_ts,
                user_id=user_id,
                session=session,
                user_question=text,
                project_id=project_id,
            )
            
            if state is None:
                # No projects configured - yield error event
                run_id = str(uuid4())
                yield RunErrorEvent(
                    thread_id=thread_ts,
                    run_id=run_id,
                    error="No projects configured. Please add projects first."
                )
                return
            
            # Add the user message to state
            user_message = HumanMessage(content=text)
            state["messages"].append(user_message)
            state["user_id"] = user_id
            
            # Calculate message index for stable ID generation
            message_index = len([m for m in state["messages"] if isinstance(m, AIMessage)])
            
            # Get the graph
            graph = get_graph()
            
            # Generate run ID
            run_id = str(uuid4())
            
            # Accumulate AI response during streaming
            ai_response_content = ""
            
            # Stream AG-UI events
            # Note: stream_agui_events() wraps graph.astream_events() which
            # executes the graph and streams events. We don't need to re-invoke.
            async for agui_event in stream_agui_events(
                graph=graph,
                state=state,
                thread_id=thread_ts,
                run_id=run_id,
                message_index=message_index,
            ):
                # Capture AI message content from streaming events
                if agui_event.type == "textMessageContent":
                    ai_response_content += agui_event.delta or ""
                
                yield agui_event
            
            # After streaming, manually add the AI message to state
            # (astream_events doesn't modify state in-place like ainvoke does)
            if ai_response_content:
                ai_message = AIMessage(content=ai_response_content)
                state["messages"].append(ai_message)
            
            # Update cached state
            self._conversations[conversation_key] = state
            
            # Save state to database
            await self._save_state(
                channel_id=channel_id,
                thread_ts=thread_ts,
                user_id=user_id,
                state=state,
                session=session,
            )
            
            logger.info(f"Completed streaming for {conversation_key}")
            
        except Exception as e:
            logger.error(f"Error in streaming handler: {e}", exc_info=True)
            run_id = str(uuid4())
            yield RunErrorEvent(
                thread_id=thread_ts,
                run_id=run_id,
                error=str(e)
            )
    
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
        project_id: Optional[str] = None,
    ) -> Optional[SlineState]:
        """
        Get existing conversation state or create new one.
        
        Uses LLM-based project classification to determine which project
        the user is asking about, unless project_id is provided (dashboard).
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Slack thread timestamp
            user_id: Slack user ID
            session: Database session
            user_question: The user's question (for project classification)
            project_id: Optional project ID (dashboard-specific context)
        
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
        # Determine which project to use
        project = None
        
        # If project_id provided (dashboard), use it directly
        if project_id:
            try:
                project_uuid = UUID(project_id)
                result = await session.execute(
                    select(ProjectModel).filter(ProjectModel.id == project_uuid)
                )
                project = result.scalar_one_or_none()
                
                if project:
                    logger.info(f"Using dashboard-selected project: {project.name}")
                else:
                    logger.warning(f"Project {project_id} not found, falling back to classifier")
            except ValueError:
                logger.error(f"Invalid project_id format: {project_id}")
        
        # If no project yet (Slack or invalid project_id), use LLM classifier
        if not project:
            all_projects = await self._get_all_projects(session)
            
            if not all_projects:
                logger.warning("No projects configured in the system")
                return None
            
            from .classifier import classify_project
            from .brain import get_llm_model
            
            project = await classify_project(
                user_question=user_question,
                projects=all_projects,
                llm_model=get_llm_model()
            )
            
            logger.info(f"LLM classifier selected project '{project.name}' for conversation {conversation_key}")
        
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
        
        Uses WorkspaceManager to:
        - Clone repository on first use
        - Pull latest changes on subsequent uses
        
        Args:
            project: Project model
        
        Returns:
            Absolute path to workspace
        
        Raises:
            GitError: If cloning or pulling fails
        """
        workspace_manager = get_workspace_manager()
        
        try:
            workspace_path = await workspace_manager.get_workspace(project)
            return workspace_path
        except GitError as e:
            logger.error(f"Failed to get workspace for {project.name}: {e}")
            # Re-raise to let caller handle it
            raise
    
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
            
            # Generate title from first user message if not already set
            title = None
            if not conversation or not conversation.title:
                title = self._generate_title(state)
            
            if conversation:
                # Update existing conversation
                conversation.state_json = state_json
                conversation.update_metadata(user_id)
                if title:
                    conversation.title = title
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
                    title=title or "New conversation",
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
    
    def _generate_title(self, state: SlineState) -> str:
        """
        Generate a conversation title from the first user message.
        
        Args:
            state: SlineState
        
        Returns:
            Title string (max 60 chars)
        """
        messages = state.get("messages", [])
        
        # Find first user message
        for msg in messages:
            if isinstance(msg, HumanMessage):
                content = msg.content.strip()
                if content:
                    # Truncate to 60 chars
                    if len(content) > 60:
                        return content[:60] + "..."
                    return content
        
        return "New conversation"


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
