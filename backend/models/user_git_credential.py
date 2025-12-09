"""
User Git Credential model for storing per-user GitHub authentication.

This model stores each user's GitHub credentials so that commits appear
as the actual user who requested the task, rather than a shared bot account.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class UserGitCredentialModel(Base):
    """
    Model for storing user-specific GitHub credentials.
    
    Each Slack user connects their own GitHub account, and their credentials
    are used when executing tasks they request. This ensures proper commit
    attribution and respects per-user GitHub permissions.
    """
    
    __tablename__ = "user_git_credentials"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Tenant information
    tenant_id = Column(String(255), nullable=False, index=True)
    
    # Slack user information
    slack_user_id = Column(String(255), nullable=False, index=True)
    slack_username = Column(String(255), nullable=True)
    
    # GitHub OAuth credentials
    github_username = Column(String(255), nullable=True)
    github_access_token = Column(Text, nullable=True)  # TODO: Encrypt in production
    github_refresh_token = Column(Text, nullable=True)  # TODO: Encrypt in production
    token_expires_at = Column(DateTime, nullable=True)
    
    # Git commit identity (for git config)
    git_user_name = Column(String(255), nullable=True)  # e.g., "Alice Smith"
    git_user_email = Column(String(255), nullable=True)  # e.g., "alice@company.com"
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<UserGitCredentialModel(id={self.id}, slack_user={self.slack_user_id}, github={self.github_username})>"
    
    @classmethod
    def find_by_slack_user(cls, session, tenant_id: str, slack_user_id: str):
        """
        Find a user's credentials by tenant and Slack user ID.
        
        Args:
            session: Database session
            tenant_id: Tenant identifier
            slack_user_id: Slack user ID
            
        Returns:
            UserGitCredentialModel or None if not found
        """
        return session.query(cls).filter(
            cls.tenant_id == tenant_id,
            cls.slack_user_id == slack_user_id
        ).first()
    
    def is_connected(self) -> bool:
        """Check if user has connected their GitHub account."""
        return bool(
            self.github_access_token is not None 
            and self.git_user_name is not None 
            and self.git_user_email is not None
        )
    
    def needs_refresh(self) -> bool:
        """Check if the access token needs to be refreshed."""
        if self.token_expires_at is None:
            return False
        return bool(datetime.utcnow() >= self.token_expires_at)
