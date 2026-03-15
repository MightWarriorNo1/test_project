"""Build grid graph and reduced incidence matrix for KCL (A @ i = 0)."""

from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np

from ntl_engine.domain.types import NodeType
from ntl_engine.domain.types import EdgeAttr


# Type alias: node id -> type, edge (u,v) -> EdgeAttr
GridGraph = nx.DiGraph


def add_node_with_type(G: GridGraph, node_id: str, node_type: NodeType) -> None:
    """Add a node with NodeType attribute."""
    G.add_node(node_id, node_type=node_type)


def add_edge_with_attr(
    G: GridGraph,
    u: str,
    v: str,
    R: float,
    X: float,
    Max_Capacity: float,
    L: Optional[float] = None,
) -> None:
    """Add directed edge (cable) with R, X, Max_Capacity (and optional L)."""
    attr: Dict[str, Any] = {
        "R": R,
        "X": X,
        "Max_Capacity": Max_Capacity,
    }
    if L is not None:
        attr["L"] = L
    G.add_edge(u, v, **attr)


def build_incidence_matrix(
    G: GridGraph,
    reference_node: Optional[str] = None,
    branch_order: Optional[List[Tuple[str, str]]] = None,
) -> Tuple[np.ndarray, List[str], List[Tuple[str, str]]]:
    """
    Build reduced branch-node incidence matrix A such that KCL is A @ i = 0.

    Convention: +1 if branch leaves node, -1 if branch enters node.
    Returns: (A_reduced, node_list_without_ref, edge_list).
    A_reduced has shape (n_nodes - 1, n_edges). branch_order defaults to G.edges().
    """
    nodes = list(G.nodes())
    if branch_order is None:
        edges = list(G.edges())
    else:
        edges = branch_order

    if reference_node is None:
        reference_node = nodes[0]
    if reference_node not in nodes:
        raise ValueError(f"Reference node {reference_node} not in graph")

    nodes_without_ref = [n for n in nodes if n != reference_node]
    n_nodes_reduced = len(nodes_without_ref)
    n_edges = len(edges)
    node_index = {n: i for i, n in enumerate(nodes_without_ref)}
    edge_index = {e: j for j, e in enumerate(edges)}

    A = np.zeros((n_nodes_reduced, n_edges), dtype=np.float64)
    for (u, v), j in edge_index.items():
        if u == reference_node:
            # Branch leaves reference -> enters node v -> -1 at row v
            if v in node_index:
                A[node_index[v], j] = -1.0
        elif v == reference_node:
            # Branch enters reference -> leaves node u -> +1 at row u
            if u in node_index:
                A[node_index[u], j] = 1.0
        else:
            if u in node_index:
                A[node_index[u], j] = 1.0
            if v in node_index:
                A[node_index[v], j] = -1.0

    return A, nodes_without_ref, edges


def get_branch_attributes(
    G: GridGraph,
    edge_list: List[Tuple[str, str]],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Return vectors R, X, Max_Capacity for the given edge list (same order as A columns).
    """
    R = np.array([G.edges[e].get("R", 0.0) for e in edge_list], dtype=np.float64)
    X = np.array([G.edges[e].get("X", 0.0) for e in edge_list], dtype=np.float64)
    Max_Capacity = np.array(
        [G.edges[e].get("Max_Capacity", np.inf) for e in edge_list],
        dtype=np.float64,
    )
    return R, X, Max_Capacity
