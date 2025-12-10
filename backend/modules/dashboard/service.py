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
    
    async def get_project(
        self,
        session: AsyncSession,
        project_id: str
    ) -> Optional[ProjectModel]:
        """
        Get a single project by ID.
        
        Args:
            session: Database session
            project_id: Project UUID
            
        Returns:
            ProjectModel instance or None if not found
        """
        result = await session.execute(
            select(ProjectModel).where(ProjectModel.id == UUID(project_id))
        )
        return result.scalar_one_or_none()
    
    async def get_project_rules(self, project: ProjectModel) -> str:
        """
        Get agent rules (.clinerules) content for a project.
        
        Args:
            project: ProjectModel instance
            
        Returns:
            str: Content of .clinerules file or empty string
        """
        if not project.workspace_path:
            return ""
        
        rules_path = os.path.join(project.workspace_path, ".clinerules")
        
        if os.path.exists(rules_path):
            with open(rules_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        return ""
    
    async def update_project_rules(self, project: ProjectModel, content: str) -> None:
        """
        Update agent rules (.clinerules) for a project.
        
        Args:
            project: ProjectModel instance
            content: New rules content
        """
        if not project.workspace_path:
            raise ValueError("Project workspace path not configured")
        
        # Ensure workspace directory exists
        os.makedirs(project.workspace_path, exist_ok=True)
        
        rules_path = os.path.join(project.workspace_path, ".clinerules")
        
        with open(rules_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Updated rules for project {project.id}")
    
    async def delete_project_rules(self, project: ProjectModel) -> None:
        """
        Delete agent rules (.clinerules) for a project.
        
        Args:
            project: ProjectModel instance
        """
        if not project.workspace_path:
            return
        
        rules_path = os.path.join(project.workspace_path, ".clinerules")
        
        if os.path.exists(rules_path):
            os.remove(rules_path)
            logger.info(f"Deleted rules for project {project.id}")
    
    async def list_workflows(self, project: ProjectModel) -> List[str]:
        """
        List all workflows for a project.
        
        Args:
            project: ProjectModel instance
            
        Returns:
            List of workflow names (without .md extension)
        """
        if not project.workspace_path:
            return []
        
        workflows_dir = os.path.join(project.workspace_path, ".clineworkflows")
        
        if not os.path.exists(workflows_dir):
            return []
        
        workflows = []
        for filename in os.listdir(workflows_dir):
            if filename.endswith('.md'):
                workflows.append(filename[:-3])  # Remove .md extension
        
        return sorted(workflows)
    
    async def get_workflow(self, project: ProjectModel, workflow_name: str) -> str:
        """
        Get content of a specific workflow.
        
        Args:
            project: ProjectModel instance
            workflow_name: Workflow name (without .md extension)
            
        Returns:
            str: Workflow content
            
        Raises:
            FileNotFoundError: If workflow doesn't exist
        """
        if not project.workspace_path:
            raise FileNotFoundError(f"Workflow '{workflow_name}' not found")
        
        workflow_path = os.path.join(
            project.workspace_path,
            ".clineworkflows",
            f"{workflow_name}.md"
        )
        
        if not os.path.exists(workflow_path):
            raise FileNotFoundError(f"Workflow '{workflow_name}' not found")
        
        with open(workflow_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    async def update_workflow(
        self,
        project: ProjectModel,
        workflow_name: str,
        content: str
    ) -> None:
        """
        Update a workflow's content.
        
        Args:
            project: ProjectModel instance
            workflow_name: Workflow name (without .md extension)
            content: New workflow content
        """
        if not project.workspace_path:
            raise ValueError("Project workspace path not configured")
        
        workflows_dir = os.path.join(project.workspace_path, ".clineworkflows")
        os.makedirs(workflows_dir, exist_ok=True)
        
        workflow_path = os.path.join(workflows_dir, f"{workflow_name}.md")
        
        with open(workflow_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Updated workflow '{workflow_name}' for project {project.id}")
    
    async def create_workflow(
        self,
        project: ProjectModel,
        workflow_name: str,
        content: str
    ) -> None:
        """
        Create a new workflow.
        
        Args:
            project: ProjectModel instance
            workflow_name: Workflow name (without .md extension)
            content: Workflow content
        """
        await self.update_workflow(project, workflow_name, content)
    
    async def delete_workflow(
        self,
        project: ProjectModel,
        workflow_name: str
    ) -> None:
        """
        Delete a workflow.
        
        Args:
            project: ProjectModel instance
            workflow_name: Workflow name (without .md extension)
            
        Raises:
            FileNotFoundError: If workflow doesn't exist
        """
        if not project.workspace_path:
            raise FileNotFoundError(f"Workflow '{workflow_name}' not found")
        
        workflow_path = os.path.join(
            project.workspace_path,
            ".clineworkflows",
            f"{workflow_name}.md"
        )
        
        if not os.path.exists(workflow_path):
            raise FileNotFoundError(f"Workflow '{workflow_name}' not found")
        
        os.remove(workflow_path)
        logger.info(f"Deleted workflow '{workflow_name}' for project {project.id}")
    
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
