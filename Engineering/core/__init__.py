"""
Universal Prompt Studio

Engineering Core Package
"""

from .paths import ProjectPaths, get_paths
from .version import VERSION

__all__ = [
    "VERSION",
    "ProjectPaths",
    "get_paths",
]