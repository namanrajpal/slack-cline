"""
Project model for mapping Slack channels to Git repositories.

This model stores the configuration that maps Slack channels to specific
Git repositories, enabling the system to know which repo to operate on
when a command is issued in a particular channel.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class ProjectModel(Base):
    """
    Model for storing Slack channel to repository mappings.
    
    This model represents the configuration that determines which Git repository
    should be used when a Cline command is issued in a specific Slack channel.
    """
    
    __tablename__ = "projects"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Tenant information (for multi-tenant support)
    tenant_id = Column(String(255), nullable=False, index=True)
    
    # Slack channel configuration
    slack_channel_id = Column(String(255), nullable=False, index=True)
    
    # Repository configuration
    repo_url = Column(String(512), nullable=False)
    default_ref = Column(String(255), nullable=False, default="main")
    
    # Workspace configuration (persistent workspace per project)
    workspace_path = Column(String(512), nullable=True)  # e.g., /workspaces/project-{id}
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    runs = relationship("RunModel", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ProjectModel(id={self.id}, channel={self.slack_channel_id}, repo={self.repo_url})>"
    
    @classmethod
    def find_by_channel(cls, session, tenant_id: str, slack_channel_id: str):
        """
        Find a project by tenant and Slack channel.
        
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
