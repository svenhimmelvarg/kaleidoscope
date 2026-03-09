"""Workflow truncation logic for ComfyUI API prompts."""

import logging
from typing import Optional, Set
from .graph import parse_graph, Graph

logger = logging.getLogger(__name__)


def _get_dependencies_recursive(
    graph: Graph, node_id: str, visited: Optional[Set[str]] = None
) -> Set[str]:
    """Recursively collect all dependencies of a node by traversing backward through inputs.

    Args:
        graph: The workflow graph
        node_id: Node to start from
        visited: Set of already visited node IDs (for recursion)

    Returns:
        Set of all node IDs that the target node depends on (including itself)
    """
    if visited is None:
        visited = set()

    # Skip if already visited or node doesn't exist
    if node_id in visited or node_id not in graph:
        return visited

    # Add this node to visited
    visited.add(node_id)

    # Get the node object
    node = graph[node_id]

    # Follow all input connections backward
    for input_refs in node.inputs.values():
        for ref in input_refs:
            # ref.node is the ID of a node this input depends on
            _get_dependencies_recursive(graph, ref.node, visited)

    return visited


def truncate_prompt_to_node(prompt: dict, output_node_id: str) -> Optional[dict]:
    """Truncate prompt to include only nodes that are dependencies of output_node_id.

    Traverses backward through the graph from the output node, following input
    connections to find all nodes that are actually required to produce the output.

    Args:
        prompt: API prompt dict (png_prompt format) where keys are node IDs
        output_node_id: Node ID to truncate at (string)

    Returns:
        Filtered dict containing only nodes that are dependencies of output_node_id,
        or None if:
        - output_node_id not found in workflow
        - Error occurs during processing

    Example:
        >>> prompt = {
        ...     "1": {"class_type": "LoadCheckpoint", ...},
        ...     "2": {"class_type": "KSampler", "inputs": {"model": ["1", 0]}, ...},
        ...     "3": {"class_type": "SaveImage", "inputs": {"samples": ["2", 0]}, ...}
        ... }
        >>> truncate_prompt_to_node(prompt, "2")
        {"1": {...}, "2": {...}}  # Node 3 excluded
    """
    try:
        graph = parse_graph(prompt)

        # Check if output node exists
        if output_node_id not in graph:
            logger.error(f"Node {output_node_id} not found in workflow")
            return None

        # Get all dependencies by traversing backward from output node
        keep_ids = _get_dependencies_recursive(graph, output_node_id)

        # Filter original prompt to only include dependency nodes
        return {k: v for k, v in prompt.items() if k in keep_ids}

    except Exception as e:
        logger.error(f"Error truncating workflow: {e}")
        return None
