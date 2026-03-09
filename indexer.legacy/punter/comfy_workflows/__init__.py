"""ComfyUI workflow processing utilities.

This package provides tools for working with ComfyUI API prompt workflows,
including graph parsing, topological sorting, and workflow truncation.

Example:
    >>> from punter.comfy_workflows import truncate_prompt_to_node
    >>>
    >>> # Truncate workflow to only include nodes up to SaveImage node
    >>> truncated = truncate_prompt_to_node(prompt_dict, "60")
    >>> if truncated:
    ...     print(f"Truncated workflow has {len(truncated)} nodes")
"""

from .truncator import truncate_prompt_to_node

__all__ = ["truncate_prompt_to_node"]
