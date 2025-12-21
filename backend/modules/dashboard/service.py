"""
Dashboard service for managing projects, runs, and configuration.

This module provides business logic for the dashboard API, including
project CRUD, run queries, API key management, and Slack command simulation.
"""

import os
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.project import ProjectModel
from models.run import RunModel, RunStatus
from models.mcp_server import McpServerModel, McpServerType
from schemas.dashboard import (
    ProjectCreateSchema,
    ProjectUpdateSchema,
    ApiKeyConfigSchema,
    TestSlackCommandSchema,
    TestSlackResponseSchema,
    McpServerCreateSchema,
    McpServerUpdateSchema
)
from utils.logging import get_logger

logger = get_logger("dashboard.service")


class DashboardService:
    """Service for dashboard operations."""
    
    async def get_projects(self, session: AsyncSession) -> List[ProjectModel]:
        """
        Get all projects.
        
        Args:
            session: Database session
            
        Returns:
            List of ProjectModel instances
        """
        result = await session.execute(
            select(ProjectModel).order_by(ProjectModel.created_at.desc())
        )
        return result.scalars().all()
    
    async def create_project(
        self, 
        data: ProjectCreateSchema, 
        session: AsyncSession
    ) -> ProjectModel:
        """
        Create a new project.
        
        Args:
            data: Project creation data
            session: Database session
            
        Returns:
            Created ProjectModel instance
        """
        project = ProjectModel(
            tenant_id=data.tenant_id,
            name=data.name,
            description=data.description,
            slack_channel_id=data.slack_channel_id,
            repo_url=data.repo_url,
            default_ref=data.default_ref
        )
        
        session.add(project)
        await session.commit()
        await session.refresh(project)
        
        logger.info(f"Created project '{project.name}' ({project.id})")
        return project
    
    async def update_project(
        self,
        project_id: str,
        data: ProjectUpdateSchema,
        session: AsyncSession
    ) -> ProjectModel:
        """
        Update an existing project.
        
        Args:
            project_id: Project UUID
            data: Update data
            session: Database session
            
        Returns:
            Updated ProjectModel instance
            
        Raises:
            ValueError: If project not found
        """
        result = await session.execute(
            select(ProjectModel).where(ProjectModel.id == UUID(project_id))
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Update fields if provided
        if data.name is not None:
            project.name = data.name
        if data.description is not None:
            project.description = data.description
        if data.slack_channel_id is not None:
            project.slack_channel_id = data.slack_channel_id
        if data.repo_url is not None:
            project.repo_url = data.repo_url
        if data.default_ref is not None:
            project.default_ref = data.default_ref
        
        await session.commit()
        await session.refresh(project)
        
        logger.info(f"Updated project {project_id}")
        return project
    
    async def delete_project(
        self,
        project_id: str,
        session: AsyncSession
    ) -> bool:
        """
        Delete a project.
        
        Args:
            project_id: Project UUID
            session: Database session
            
        Returns:
            True if deleted, False if not found
        """
        result = await session.execute(
            select(ProjectModel).where(ProjectModel.id == UUID(project_id))
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return False
        
        await session.delete(project)
        await session.commit()
        
        logger.info(f"Deleted project {project_id}")
        return True
    
    async def get_runs(
        self,
        session: AsyncSession,
        status: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 50
    ) -> List[RunModel]:
        """
        Get runs with optional filters.
        
        Args:
            session: Database session
            status: Filter by status
            project_id: Filter by project
            limit: Maximum number of results
            
        Returns:
            List of RunModel instances
        """
        query = select(RunModel).order_by(desc(RunModel.created_at)).limit(limit)
        
        # Apply filters
        if status:
            try:
                status_enum = RunStatus(status)
                query = query.where(RunModel.status == status_enum)
            except ValueError:
                logger.warning(f"Invalid status filter: {status}")
        
        if project_id:
            query = query.where(RunModel.project_id == UUID(project_id))
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def get_run_details(
        self,
        run_id: str,
        session: AsyncSession
    ) -> Optional[RunModel]:
        """
        Get detailed information for a single run.
        
        Args:
            run_id: Run UUID
            session: Database session
            
        Returns:
            RunModel instance or None if not found
        """
        result = await session.execute(
            select(RunModel).where(RunModel.id == UUID(run_id))
        )
        return result.scalar_one_or_none()
    
    def get_api_config(self) -> ApiKeyConfigSchema:
        """
        Get current API key configuration from environment.
        
        Returns:
            ApiKeyConfigSchema with current settings
        """
        return ApiKeyConfigSchema(
            provider=settings.cline_provider,
            api_key=settings.cline_api_key,
            model_id=settings.cline_model_id,
            base_url=settings.cline_base_url or ""
        )
    
    def update_api_config(self, config: ApiKeyConfigSchema) -> dict:
        """
        Update API key configuration in .env file.
        
        NOTE: This requires a backend restart to take effect!
        
        Args:
            config: New API key configuration
            
        Returns:
            dict with status and message
        """
        try:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
            
            # Read existing .env file
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    lines = f.readlines()
            else:
                lines = []
            
            # Update or add configuration lines
            new_lines = []
            keys_to_update = {
                'CLINE_PROVIDER': config.provider,
                'CLINE_API_KEY': config.api_key,
                'CLINE_MODEL_ID': config.model_id,
                'CLINE_BASE_URL': config.base_url or ''
            }
            
            updated_keys = set()
            
            for line in lines:
                line_stripped = line.strip()
                if line_stripped and not line_stripped.startswith('#'):
                    key = line_stripped.split('=')[0]
                    if key in keys_to_update:
                        new_lines.append(f"{key}={keys_to_update[key]}\n")
                        updated_keys.add(key)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            
            # Add any missing keys
            for key, value in keys_to_update.items():
                if key not in updated_keys:
                    new_lines.append(f"{key}={value}\n")
            
            # Write back to .env file
            with open(env_path, 'w') as f:
                f.writelines(new_lines)
            
            logger.info("Updated API configuration in .env file")
            
            return {
                "success": True,
                "message": "Configuration updated successfully. Please restart the backend for changes to take effect.",
                "restart_required": True
            }
            
        except Exception as e:
            logger.error(f"Failed to update .env file: {e}")
            return {
                "success": False,
                "message": f"Failed to update configuration: {str(e)}",
                "restart_required": False
            }
    
    async def get_mcp_servers(self, session: AsyncSession) -> List[McpServerModel]:
        """
        Get all MCP servers.
        
        Args:
            session: Database session
            
        Returns:
            List of McpServerModel instances
        """
        result = await session.execute(
            select(McpServerModel).order_by(McpServerModel.created_at.desc())
        )
        return result.scalars().all()
    
    async def create_mcp_server(
        self,
        data: McpServerCreateSchema,
        session: AsyncSession
    ) -> McpServerModel:
        """
        Create a new MCP server.
        
        Args:
            data: MCP server creation data
            session: Database session
            
        Returns:
            Created McpServerModel instance
            
        Raises:
            ValueError: If invalid server type or missing required fields
        """
        try:
            server_type = McpServerType(data.type)
        except ValueError:
            raise ValueError(f"Invalid server type: {data.type}. Must be 'stdio' or 'http'")
        
        # Validate required fields based on server type
        if server_type == McpServerType.STDIO:
            if not data.command:
                raise ValueError("Command is required for stdio servers")
        elif server_type == McpServerType.STREAMABLE_HTTP:
            if not data.url:
                raise ValueError("URL is required for HTTP servers")
        
        server = McpServerModel(
            name=data.name,
            type=server_type,
            url=data.url,
            command=data.command,
            args=data.args
        )
        
        session.add(server)
        await session.commit()
        await session.refresh(server)
        
        logger.info(f"Created MCP server '{server.name}' ({server.id})")
        return server
    
    async def update_mcp_server(
        self,
        server_id: str,
        data: McpServerUpdateSchema,
        session: AsyncSession
    ) -> McpServerModel:
        """
        Update an existing MCP server.
        
        Args:
            server_id: MCP server UUID
            data: Update data
            session: Database session
            
        Returns:
            Updated McpServerModel instance
            
        Raises:
            ValueError: If server not found, invalid type, or missing required fields
        """
        result = await session.execute(
            select(McpServerModel).where(McpServerModel.id == UUID(server_id))
        )
        server = result.scalar_one_or_none()
        
        if not server:
            raise ValueError(f"MCP server {server_id} not found")
        
        # Determine the server type after update (use new type if provided, otherwise current)
        updated_type = server.type
        if data.type is not None:
            try:
                updated_type = McpServerType(data.type)
            except ValueError:
                raise ValueError(f"Invalid server type: {data.type}. Must be 'stdio' or 'http'")
        
        if data.name is not None:
            server.name = data.name
        if data.type is not None:
            server.type = updated_type
        if data.url is not None:
            server.url = data.url
        if data.command is not None:
            server.command = data.command
        if data.args is not None:
            server.args = data.args
        
        # Validate required fields based on server type after update
        if updated_type == McpServerType.STDIO:
            if not server.command:
                raise ValueError("Command is required for stdio servers")
        elif updated_type == McpServerType.STREAMABLE_HTTP:
            if not server.url:
                raise ValueError("URL is required for HTTP servers")
        
        await session.commit()
        await session.refresh(server)
        
        logger.info(f"Updated MCP server {server_id}")
        return server
    
    async def delete_mcp_server(
        self,
        server_id: str,
        session: AsyncSession
    ) -> bool:
        """
        Delete an MCP server.
        
        Args:
            server_id: MCP server UUID
            session: Database session
            
        Returns:
            True if deleted, False if not found
        """
        result = await session.execute(
            select(McpServerModel).where(McpServerModel.id == UUID(server_id))
        )
        server = result.scalar_one_or_none()
        
        if not server:
            return False
        
        await session.delete(server)
        await session.commit()
        
        logger.info(f"Deleted MCP server {server_id}")
        return True


# Global service instance
_dashboard_service: Optional[DashboardService] = None


def get_dashboard_service() -> DashboardService:
    """
    Get or create the global dashboard service instance.
    
    Returns:
        DashboardService: Service instance
    """
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = DashboardService()
    return _dashboard_service
