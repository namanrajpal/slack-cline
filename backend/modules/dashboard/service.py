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
from schemas.dashboard import (
    ProjectCreateSchema,
    ProjectUpdateSchema,
    ApiKeyConfigSchema,
    TestSlackCommandSchema,
    TestSlackResponseSchema
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
