"""
Sline Tools Module

Contains tool factories for SlineBrain.
Tools are created with workspace_path bound via closure so the LLM
only sees user-facing parameters.
"""

from .factory import make_bound_tools

__all__ = ["make_bound_tools"]
