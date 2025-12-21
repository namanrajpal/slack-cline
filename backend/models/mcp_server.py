"""
MCP (Model Context Protocol) server model.

This model stores MCP server configurations with id, name, type, and url.
"""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID

from database import Base

class McpServerType(enum.Enum):
    """MCP server type enumeration."""
    STDIO = "stdio"
    STREAMABLE_HTTP = "http"



class McpServerModel(Base):
    """
    Model for storing MCP server configurations.
    
    Fields:
    - id: UUID primary key
    - name: Server name
    - type: Server type (stdio or http)
    - url: Server URL
    """
    
    __tablename__ = "mcp_servers"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Server name
    name = Column(String(255), nullable=False, unique=True, index=True)
    
    # Server type: stdio or http
    type = Column(Enum(McpServerType), nullable=False, index=True)
    
    # Server URL
    url = Column(String(512), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<McpServerModel(id={self.id}, name={self.name}, type={self.type.value}, url={self.url})>"
