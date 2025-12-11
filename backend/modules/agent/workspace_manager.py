"""
Workspace Manager

Handles git repository cloning, caching, and refreshing for projects.
Ensures workspaces always have the latest code.
"""

import asyncio
import os
import re
import shutil
from pathlib import Path
from typing import Optional

from models.project import ProjectModel
from utils.logging import get_logger

logger = get_logger("agent.workspace_manager")


class GitError(Exception):
    """Raised when git operations fail."""
    pass


class WorkspaceManager:
    """
    Manages git repository workspaces for projects.
    
    Strategy:
    - Clone repository on first use
    - Pull latest changes before every subsequent use
    - Cache clones in /data/workspaces/<project-name-slug>/
    - One workspace per project (reused across conversations)
    - Automatic cleanup of corrupted workspaces (no .git directory)
    
    Attributes:
        workspace_base: Base directory for all workspaces (default: /data/workspaces)
    
    Examples:
        Project "Slack-Sline" → /data/workspaces/slack-sline/
        Project "My API (v2)" → /data/workspaces/my-api-v2/
    """
    
    def __init__(self, workspace_base: str = "/data/workspaces"):
        """
        Initialize workspace manager.
        
        Args:
            workspace_base: Base directory for storing workspace clones
        """
        self.workspace_base = workspace_base
        os.makedirs(workspace_base, exist_ok=True)
        logger.info(f"WorkspaceManager initialized, base: {workspace_base}")
    
    def _slugify(self, name: str) -> str:
        """
        Convert project name to filesystem-safe slug.
        
        - Convert to lowercase
        - Replace spaces and special chars with hyphens
        - Remove consecutive hyphens
        - Strip leading/trailing hyphens
        
        Examples:
            "My Project" → "my-project"
            "API Service (v2)" → "api-service-v2"
            "frontend_app" → "frontend-app"
        
        Args:
            name: Project name to slugify
        
        Returns:
            Filesystem-safe slug string
        """
        # Convert to lowercase
        slug = name.lower()
        
        # Replace spaces and underscores with hyphens
        slug = slug.replace(' ', '-').replace('_', '-')
        
        # Remove all non-alphanumeric characters except hyphens
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        
        # Replace consecutive hyphens with single hyphen
        slug = re.sub(r'-+', '-', slug)
        
        # Strip leading/trailing hyphens
        slug = slug.strip('-')
        
        # Fallback to 'workspace' if slug is empty
        if not slug:
            slug = 'workspace'
        
        return slug
    
    async def get_workspace(self, project: ProjectModel) -> str:
        """
        Get workspace path for a project, cloning or updating as needed.
        
        This is the main entry point for getting a workspace.
        
        Strategy:
        1. If workspace is valid (has .git) → Pull latest changes
        2. If workspace directory exists but is corrupted (no .git) → Clean up and re-clone
        3. If workspace doesn't exist → Clone
        4. Return absolute path to workspace
        
        Args:
            project: ProjectModel with repo_url and default_ref
        
        Returns:
            Absolute path to workspace directory
        
        Raises:
            GitError: If cloning or pulling fails
        """
        workspace_path = self._get_workspace_path(project)
        
        if self._is_valid_workspace(workspace_path):
            # Workspace exists and is valid - pull latest changes
            logger.info(f"Workspace exists, pulling latest changes: {project.name}")
            try:
                await self._pull_repository(workspace_path, project.default_ref)
                logger.info(f"Successfully pulled latest changes for {project.name}")
            except GitError as e:
                # If pull fails, log warning but continue (use existing code)
                logger.warning(f"Failed to pull updates for {project.name}: {e}")
                logger.info(f"Continuing with existing workspace at {workspace_path}")
        else:
            # Check if directory exists but is not a valid git repository (corrupted)
            if os.path.exists(workspace_path):
                logger.warning(f"Corrupted workspace detected for {project.name} at {workspace_path}")
                logger.info(f"Directory exists but is not a valid git repository - cleaning up...")
                
                try:
                    # Remove corrupted directory
                    shutil.rmtree(workspace_path)
                    logger.info(f"Successfully cleaned up corrupted workspace")
                except Exception as e:
                    logger.error(f"Failed to clean up corrupted workspace: {e}", exc_info=True)
                    raise GitError(f"Failed to clean up corrupted workspace at {workspace_path}: {e}")
            
            # Clone repository (either first time or after cleanup)
            logger.info(f"Cloning repository {project.repo_url} to {workspace_path}")
            await self._clone_repository(
                repo_url=project.repo_url,
                destination=workspace_path,
                ref=project.default_ref
            )
            logger.info(f"Successfully cloned {project.name}")
        
        return workspace_path
    
    def _get_workspace_path(self, project: ProjectModel) -> str:
        """
        Get workspace path for a project using human-readable slug.
        
        Args:
            project: ProjectModel
        
        Returns:
            Absolute path to workspace directory (e.g., /data/workspaces/my-project/)
        """
        slug = self._slugify(project.name)
        return os.path.join(self.workspace_base, slug)
    
    def _is_valid_workspace(self, path: str) -> bool:
        """
        Check if a workspace is valid (exists and has .git directory).
        
        Args:
            path: Workspace directory path
        
        Returns:
            True if workspace exists and appears to be a git repository
        """
        if not os.path.exists(path):
            return False
        
        git_dir = os.path.join(path, ".git")
        return os.path.isdir(git_dir)
    
    async def _clone_repository(
        self,
        repo_url: str,
        destination: str,
        ref: str = "main"
    ) -> None:
        """
        Clone a git repository.
        
        Args:
            repo_url: Git repository URL (HTTPS or SSH)
            destination: Destination directory path
            ref: Branch, tag, or commit to clone
        
        Raises:
            GitError: If cloning fails
        """
        # Ensure parent directory exists
        parent_dir = os.path.dirname(destination)
        os.makedirs(parent_dir, exist_ok=True)
        
        # Build git clone command
        # Use --depth 1 for faster cloning (shallow clone)
        cmd = [
            "git", "clone",
            "--depth", "1",
            "--single-branch",
            "--branch", ref,
            repo_url,
            destination
        ]
        
        logger.debug(f"Executing: {' '.join(cmd)}")
        
        try:
            # Execute git clone asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=parent_dir
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='replace')
                logger.error(f"Git clone failed: {error_msg}")
                raise GitError(f"Failed to clone repository: {error_msg}")
            
            logger.debug(f"Git clone output: {stdout.decode('utf-8', errors='replace')}")
            
        except FileNotFoundError:
            raise GitError("Git command not found. Ensure git is installed in the container.")
        except Exception as e:
            logger.error(f"Unexpected error during git clone: {e}", exc_info=True)
            raise GitError(f"Failed to clone repository: {str(e)}")
    
    async def _pull_repository(self, workspace_path: str, ref: str = "main") -> None:
        """
        Pull latest changes from remote repository.
        
        Args:
            workspace_path: Path to existing git repository
            ref: Branch to pull from
        
        Raises:
            GitError: If pulling fails
        """
        # Build git pull command
        cmd = ["git", "pull", "origin", ref]
        
        logger.debug(f"Executing: {' '.join(cmd)} in {workspace_path}")
        
        try:
            # Execute git pull asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_path
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='replace')
                logger.error(f"Git pull failed: {error_msg}")
                raise GitError(f"Failed to pull updates: {error_msg}")
            
            output = stdout.decode('utf-8', errors='replace')
            logger.debug(f"Git pull output: {output}")
            
            # Check if there were updates
            if "Already up to date" in output or "Already up-to-date" in output:
                logger.info(f"Repository already up to date")
            else:
                logger.info(f"Repository updated: {output.strip()}")
            
        except FileNotFoundError:
            raise GitError("Git command not found. Ensure git is installed in the container.")
        except Exception as e:
            logger.error(f"Unexpected error during git pull: {e}", exc_info=True)
            raise GitError(f"Failed to pull updates: {str(e)}")
    
    async def refresh_workspace(self, project: ProjectModel) -> None:
        """
        Manually refresh a workspace by pulling latest changes.
        
        This is useful for forcing an update outside of normal flow.
        
        Args:
            project: ProjectModel to refresh
        
        Raises:
            GitError: If workspace doesn't exist or pull fails
        """
        workspace_path = self._get_workspace_path(project)
        
        if not self._is_valid_workspace(workspace_path):
            raise GitError(f"Workspace doesn't exist for project {project.name}")
        
        logger.info(f"Manually refreshing workspace for {project.name}")
        await self._pull_repository(workspace_path, project.default_ref)
    
    async def delete_workspace(self, project: ProjectModel) -> None:
        """
        Delete a workspace directory.
        
        Useful for cleanup or forcing a fresh clone.
        
        Args:
            project: ProjectModel whose workspace should be deleted
        """
        workspace_path = self._get_workspace_path(project)
        
        if os.path.exists(workspace_path):
            logger.info(f"Deleting workspace for {project.name}: {workspace_path}")
            shutil.rmtree(workspace_path)
            logger.info(f"Workspace deleted successfully")
        else:
            logger.warning(f"Workspace doesn't exist, nothing to delete: {workspace_path}")
    
    async def cleanup_orphaned_workspaces(self, active_project_names: set[str]) -> int:
        """
        Clean up workspaces for projects that no longer exist.
        
        Args:
            active_project_names: Set of slugified project names that should be kept
        
        Returns:
            Number of workspaces cleaned up
        """
        if not os.path.exists(self.workspace_base):
            return 0
        
        # Slugify all active project names for comparison
        active_slugs = {self._slugify(name) for name in active_project_names}
        
        cleaned_count = 0
        
        # List all workspace directories
        for workspace_name in os.listdir(self.workspace_base):
            workspace_path = os.path.join(self.workspace_base, workspace_name)
            
            # Skip if not a directory
            if not os.path.isdir(workspace_path):
                continue
            
            # Check if this workspace belongs to an active project
            if workspace_name not in active_slugs:
                logger.info(f"Cleaning up orphaned workspace: {workspace_name}")
                try:
                    shutil.rmtree(workspace_path)
                    cleaned_count += 1
                except Exception as e:
                    logger.error(f"Failed to clean up workspace {workspace_name}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} orphaned workspace(s)")
        
        return cleaned_count


# Singleton instance
_workspace_manager: Optional[WorkspaceManager] = None


def get_workspace_manager() -> WorkspaceManager:
    """
    Get the singleton WorkspaceManager instance.
    
    Returns:
        WorkspaceManager instance
    """
    global _workspace_manager
    
    if _workspace_manager is None:
        _workspace_manager = WorkspaceManager()
    
    return _workspace_manager


def reset_workspace_manager():
    """Reset the workspace manager (useful for testing)."""
    global _workspace_manager
    _workspace_manager = None
    logger.info("WorkspaceManager reset")
