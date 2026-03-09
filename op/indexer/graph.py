from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


@dataclass(frozen=True)
class PortRef:
    node: str  # referenced node id, e.g. "2"
    port: int  # input/output index, e.g. 0


@dataclass
class Node:
    id: str
    class_type: str
    inputs: Dict[str, List[PortRef]]  # input_name -> list of PortRefs (supports fan-in)
    meta: Dict
    is_changed: Optional[List[str]] = None


Graph = Dict[str, Node]  # id -> Node


def parse_graph(raw: Dict) -> Graph:
    """Convert your JSON map into Node objects."""
    graph: Graph = {}
    for nid, payload in raw.items():
        # Normalize inputs: values can be scalar, list, or ["id", idx]
        norm_inputs: Dict[str, List[PortRef]] = {}
        for inp_name, v in payload.get("inputs", {}).items():

            def to_pref(x):
                # booleans, strings, etc. are leaf literals -> no edge
                if (
                    isinstance(x, list)
                    and len(x) == 2
                    and isinstance(x[0], str)
                    and isinstance(x[1], int)
                ):
                    return PortRef(node=x[0], port=x[1])
                return None

            if isinstance(v, list) and v and isinstance(v[0], list):
                # already a list of connections
                prefs = [to_pref(x) for x in v]
            else:
                prefs = [to_pref(v)]
            # keep only actual edges
            norm_inputs[inp_name] = [p for p in prefs if p is not None]

        node = Node(
            id=nid,
            class_type=payload.get("class_type", ""),
            inputs=norm_inputs,
            meta=payload.get("_meta", {}),
            is_changed=payload.get("is_changed"),
        )
        graph[nid] = node
    return graph


def build_successors(graph: Graph) -> Dict[str, List[str]]:
    """Forward adjacency (who depends on me)."""
    succ: Dict[str, List[str]] = {nid: [] for nid in graph}
    for nid, node in graph.items():
        for refs in node.inputs.values():
            for r in refs:
                if r.node in succ:
                    succ[r.node].append(nid)
    return succ


def topological_order(graph: Graph) -> List[str]:
    """Kahn's algorithm; treats nodes with no incoming edges as sources."""
    indeg = {nid: 0 for nid in graph}
    for node in graph.values():
        for refs in node.inputs.values():
            for r in refs:
                if r.node in indeg:
                    indeg[node.id] += 1
    queue = [nid for nid, d in indeg.items() if d == 0]
    order: List[str] = []
    succ = build_successors(graph)
    while queue:
        u = queue.pop()
        order.append(u)
        for v in succ.get(u, []):
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    if len(order) != len(graph):
        raise ValueError("Graph has a cycle or missing refs.")
    return order
