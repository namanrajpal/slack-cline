"""
Conversation model for tracking Slack thread state.

This model stores conversation state per Slack thread, enabling
multi-turn conversations with state persistence across server restarts.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from database import Base


class ConversationModel(Base):
    """
    Model for storing conversation state per Slack thread.
    
    Each conversation represents a Slack thread where users interact with Sline.
    The state_json field stores the serialized SlineState including messages,
    mode, and context.
    """
    
    __tablename__ = "conversations"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Slack identifiers (composite unique constraint)
    channel_id = Column(String(255), nullable=False, index=True)
    thread_ts = Column(String(255), nullable=False, index=True)
    
    # Link to project
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    
    # Serialized state (JSON blob of SlineState)
    state_json = Column(JSON, nullable=False, default=dict)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_user_id = Column(String(255))  # Last user who interacted
    message_count = Column(Integer, default=0)
    
    # Relationships
    project = relationship("ProjectModel", back_populates="conversations")
    
    # Composite unique constraint
    __table_args__ = (
        UniqueConstraint("channel_id", "thread_ts", name="uix_channel_thread"),
    )
    
    def __repr__(self):
        return f"<ConversationModel(id={self.id}, channel={self.channel_id}, thread={self.thread_ts})>"
    
    def update_metadata(self, user_id: str):
        """
        Update conversation metadata after a new message.
        
        Args:
            user_id: Slack user ID who sent the message
        """
        self.last_user_id = user_id
        self.message_count += 1
        self.updated_at = datetime.utcnow()
