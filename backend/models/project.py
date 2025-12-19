"""
Project model for Git repositories that Sline can work with.

This model stores project configurations. Projects are identified by name
and description, allowing Sline to intelligently classify which project
a user is asking about using LLM-based classification.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class ProjectModel(Base):
    """
    Model for storing project configurations.
    
    Projects are identified by name and description, allowing Sline to
    use LLM-based classification to determine which project the user is
    asking about, rather than being tied to specific Slack channels.
    """
    
    __tablename__ = "projects"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Tenant information (for multi-tenant support)
    tenant_id = Column(String(255), nullable=False, index=True, default="default")
    
    # Project identity - used for LLM classification
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(String(1024), nullable=True)
    
    
    # Repository configuration
    repo_url = Column(String(512), nullable=False)
    default_ref = Column(String(255), nullable=False, default="main")
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversations = relationship("ConversationModel", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ProjectModel(id={self.id}, name={self.name}, repo={self.repo_url})>"
    
    @classmethod
    def find_by_channel(cls, session, tenant_id: str, slack_channel_id: str):
        """
        Find a project by tenant and Slack channel (legacy method).
        
        Args:
            session: Database session
            tenant_id: Tenant identifier
            slack_channel_id: Slack channel ID
            
        Returns:
            ProjectModel or None if not found
        """
        return session.query(cls).filter(
            cls.tenant_id == tenant_id,
            cls.slack_channel_id == slack_channel_id
        ).first()
    
    @classmethod
    def find_by_name(cls, session, name: str):
        """
        Find a project by name.
        
        Args:
            session: Database session
            name: Project name
            
        Returns:
            ProjectModel or None if not found
        """
        return session.query(cls).filter(cls.name == name).first()
