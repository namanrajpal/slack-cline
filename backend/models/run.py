"""
Run model for tracking Cline execution lifecycle.

This model stores information about individual Cline runs, including their
status, timing, and associated metadata for Slack integration.
"""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class RunStatus(enum.Enum):
    """Enumeration of possible run statuses."""
    QUEUED = "queued"
    PLANNING = "planning"  # Cline is creating a plan
    AWAITING_APPROVAL = "awaiting_approval"  # Plan is ready, waiting for user approval
    RUNNING = "running"  # Approved, executing the plan
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunModel(Base):
    """
    Model for tracking Cline run execution lifecycle.
    
    This model stores all information about individual Cline runs, from initial
    creation through completion, including Slack integration metadata.
    """
    
    __tablename__ = "runs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Tenant and project relationships
    tenant_id = Column(String(255), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    
    # Cline CLI integration
    cline_run_id = Column(String(255), nullable=True, index=True)  # Task ID from Cline CLI
    cline_instance_address = Column(String(255), nullable=True)  # Instance address (e.g., localhost:50052)
    workspace_path = Column(String(512), nullable=True)  # Path to cloned repository
    
    # Run status and execution details
    status = Column(Enum(RunStatus), nullable=False, default=RunStatus.QUEUED, index=True)
    task_prompt = Column(Text, nullable=False)
    
    # Slack integration metadata
    slack_channel_id = Column(String(255), nullable=False)
    slack_thread_ts = Column(String(255), nullable=True)  # Set after posting initial message
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)  # When Cline execution started
    finished_at = Column(DateTime, nullable=True)  # When Cline execution completed
    
    # Execution summary
    summary = Column(Text, nullable=True)  # Final summary of what was done
    
    # Relationships
    project = relationship("ProjectModel", back_populates="runs")
    
    def __repr__(self):
        return f"<RunModel(id={self.id}, status={self.status.value}, cline_id={self.cline_run_id})>"
    
    @property
    def is_active(self) -> bool:
        """Check if the run is currently active (queued or running)."""
        return self.status in (RunStatus.QUEUED, RunStatus.RUNNING)
    
    @property
    def is_completed(self) -> bool:
        """Check if the run has completed (succeeded, failed, or cancelled)."""
        return self.status in (RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED)
    
    def mark_started(self):
        """Mark the run as started with current timestamp."""
        self.status = RunStatus.RUNNING
        self.started_at = datetime.utcnow()
    
    def mark_completed(self, status: RunStatus, summary: str = None):
        """
        Mark the run as completed with given status.
        
        Args:
            status: Final status (SUCCEEDED, FAILED, or CANCELLED)
            summary: Optional summary of execution results
        """
        if status not in (RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED):
            raise ValueError(f"Invalid completion status: {status}")
        
        self.status = status
        self.finished_at = datetime.utcnow()
        if summary:
            self.summary = summary
    
    @classmethod
    def find_by_cline_id(cls, session, cline_run_id: str):
        """
        Find a run by its Cline Core run ID.
        
        Args:
            session: Database session
            cline_run_id: Cline Core run identifier
            
        Returns:
            RunModel or None if not found
        """
        return session.query(cls).filter(cls.cline_run_id == cline_run_id).first()
    
    @classmethod
    def find_active_runs(cls, session, tenant_id: str = None):
        """
        Find all active (queued or running) runs.
        
        Args:
            session: Database session
            tenant_id: Optional tenant filter
            
        Returns:
            List of active RunModel instances
        """
        query = session.query(cls).filter(cls.status.in_([RunStatus.QUEUED, RunStatus.RUNNING]))
        if tenant_id:
            query = query.filter(cls.tenant_id == tenant_id)
        return query.all()
