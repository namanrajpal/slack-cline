"""
Bound Tools Factory

Creates LangChain tools with workspace_path bound via closure.
This ensures the LLM only sees user-facing parameters (path, regex, etc.)
and cannot manipulate the workspace_path.
"""

import os
import re
from pathlib import Path
from typing import List
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from models.mcp_server import McpServerModel, McpServerType
from sqlalchemy.future import select


def make_bound_tools(workspace_path: str) -> List:
    """
    Create tools with workspace_path already bound.
    
    This factory creates tool functions that close over workspace_path,
    so the LLM only sees user-facing parameters like 'path' and 'regex'.
    
    Args:
        workspace_path: Absolute path to the workspace (cloned repo)
    
    Returns:
        List of LangChain tools ready for create_react_agent()
    """
    
    @tool
    def read_file(path: str) -> str:
        """Read contents of a file at the given path.
        
        Use this to examine source code, configuration files, or any text file
        in the codebase. Always read files before making assumptions about their content.
        
        Args:
            path: Relative path to the file (e.g., 'src/main.py', 'package.json')
        
        Returns:
            File contents as string, or error message if file not found
        """
        # Normalize and join paths safely
        abs_path = os.path.normpath(os.path.join(workspace_path, path))
        
        # Security: Ensure path doesn't escape workspace
        if not abs_path.startswith(os.path.normpath(workspace_path)):
            return f"Error: Path '{path}' is outside the workspace"
        
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Truncate very large files
                if len(content) > 50000:
                    return content[:50000] + f"\n\n... [File truncated, showing first 50000 chars of {len(content)} total]"
                return content
        except FileNotFoundError:
            return f"Error: File not found: {path}"
        except UnicodeDecodeError:
            return f"Error: Cannot read binary file: {path}"
        except PermissionError:
            return f"Error: Permission denied: {path}"
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    @tool
    def list_files(path: str = ".", recursive: bool = False) -> str:
        """List files and directories at the given path.
        
        Use this to explore the project structure and find relevant files.
        Start with non-recursive listing to understand top-level structure,
        then drill down into specific directories.
        
        Args:
            path: Directory path to list (default: workspace root ".")
            recursive: If True, list all files recursively (can be large!)
        
        Returns:
            Formatted list of files/directories, one per line
        """
        abs_path = os.path.normpath(os.path.join(workspace_path, path))
        
        # Security: Ensure path doesn't escape workspace
        if not abs_path.startswith(os.path.normpath(workspace_path)):
            return f"Error: Path '{path}' is outside the workspace"
        
        try:
            if not os.path.exists(abs_path):
                return f"Error: Directory not found: {path}"
            
            if not os.path.isdir(abs_path):
                return f"Error: Not a directory: {path}"
            
            if recursive:
                files = []
                for root, dirs, filenames in os.walk(abs_path):
                    # Skip common non-essential directories
                    dirs[:] = [d for d in dirs if d not in {
                        'node_modules', '.git', '__pycache__', 
                        '.venv', 'venv', '.tox', 'dist', 'build',
                        '.next', '.nuxt', 'coverage', '.pytest_cache'
                    }]
                    
                    for f in filenames:
                        full_path = os.path.join(root, f)
                        rel = os.path.relpath(full_path, workspace_path)
                        files.append(rel)
                
                # Limit output size
                if len(files) > 500:
                    return "\n".join(sorted(files)[:500]) + f"\n\n... [{len(files)} files total, showing first 500]"
                return "\n".join(sorted(files)) if files else "(empty directory)"
            else:
                entries = []
                for entry in os.listdir(abs_path):
                    entry_path = os.path.join(abs_path, entry)
                    if os.path.isdir(entry_path):
                        entries.append(f"{entry}/")
                    else:
                        entries.append(entry)
                return "\n".join(sorted(entries)) if entries else "(empty directory)"
                
        except PermissionError:
            return f"Error: Permission denied: {path}"
        except Exception as e:
            return f"Error listing files: {str(e)}"
    
    @tool
    def search_files(regex: str, path: str = ".", file_pattern: str = "*") -> str:
        """Search for a regex pattern across files in a directory.
        
        Use this to find specific code patterns, function definitions, imports,
        TODO comments, or any text pattern across the codebase.
        
        Args:
            regex: Regular expression pattern to search for (e.g., "def main", "TODO:", "import.*requests")
            path: Directory to search in (default: workspace root ".")
            file_pattern: Glob pattern to filter files (e.g., "*.py", "*.ts", "*.json")
        
        Returns:
            Search results with file paths, line numbers, and matching lines.
            Format: "path/to/file.py:42: matching line content"
        """
        abs_path = os.path.normpath(os.path.join(workspace_path, path))
        
        # Security: Ensure path doesn't escape workspace
        if not abs_path.startswith(os.path.normpath(workspace_path)):
            return f"Error: Path '{path}' is outside the workspace"
        
        results = []
        
        try:
            pattern = re.compile(regex, re.IGNORECASE)
        except re.error as e:
            return f"Error: Invalid regex pattern: {e}"
        
        try:
            search_path = Path(abs_path)
            
            if not search_path.exists():
                return f"Error: Path not found: {path}"
            
            # Skip common non-essential directories
            skip_dirs = {
                'node_modules', '.git', '__pycache__', 
                '.venv', 'venv', '.tox', 'dist', 'build',
                '.next', '.nuxt', 'coverage', '.pytest_cache'
            }
            
            for file_path in search_path.rglob(file_pattern):
                # Skip directories and files in skip_dirs
                if any(skip in file_path.parts for skip in skip_dirs):
                    continue
                    
                if file_path.is_file():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for i, line in enumerate(f, 1):
                                if pattern.search(line):
                                    rel_path = os.path.relpath(file_path, workspace_path)
                                    # Truncate very long lines
                                    display_line = line.rstrip()
                                    if len(display_line) > 200:
                                        display_line = display_line[:200] + "..."
                                    results.append(f"{rel_path}:{i}: {display_line}")
                                    
                                    # Limit results per file
                                    if len([r for r in results if r.startswith(rel_path)]) >= 10:
                                        break
                    except (UnicodeDecodeError, PermissionError):
                        # Skip binary files and files we can't read
                        continue
            
            if results:
                # Limit total results
                if len(results) > 100:
                    return "\n".join(results[:100]) + f"\n\n... [{len(results)} matches total, showing first 100]"
                return "\n".join(results)
            return "No matches found."
            
        except Exception as e:
            return f"Error searching: {str(e)}"
    
    # Return all tools as a list
    return [read_file, list_files, search_files]


def make_write_tools(workspace_path: str) -> List:
    """
    Create write tools (Phase 2).
    
    These tools allow modifying files and should only be enabled
    after explicit user approval of a plan.
    
    Args:
        workspace_path: Absolute path to the workspace
    
    Returns:
        List of write-capable LangChain tools
    """
    
    @tool
    def write_to_file(path: str, content: str) -> str:
        """Write content to a file (creates directories if needed).
        
        Use this to create new files or overwrite existing files.
        Always create parent directories automatically.
        
        Args:
            path: Relative path for the file (e.g., 'src/utils/helper.py')
            content: Content to write to the file
        
        Returns:
            Success message or error description
        """
        abs_path = os.path.normpath(os.path.join(workspace_path, path))
        
        # Security: Ensure path doesn't escape workspace
        if not abs_path.startswith(os.path.normpath(workspace_path)):
            return f"Error: Path '{path}' is outside the workspace"
        
        try:
            # Create parent directories
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            
            with open(abs_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"✅ Successfully wrote to {path}"
        except PermissionError:
            return f"Error: Permission denied: {path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    return [write_to_file]

async def make_mcp_tools() -> List:
    """
    Create MCP tools.
    
    Returns:
        List of MCP tools
    """

    
    # Fetch MCP servers from the database
    # INSERT_YOUR_CODE

    from database import async_session_maker
    async with async_session_maker() as session:
        result = await session.execute(select(McpServerModel))
        mcp_servers = result.scalars().all()

    if not mcp_servers:
        return None

    # Build a dictionary of MCP servers for MultiServerMCPClient
    mcp_config = {
        "airbnb": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@openbnb/mcp-server-airbnb",  "--ignore-robots-txt"],
        }
    }
    for server in mcp_servers:
        mcp_config[server.name] = {
            "transport": McpServerType(server.type).value,
            "url": server.url,
        }

    client = MultiServerMCPClient(  
        mcp_config
    )
    mcp_tools = await client.get_tools()
    return mcp_tools