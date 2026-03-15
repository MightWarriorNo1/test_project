"""Unit tests for graph build and incidence matrix."""

import numpy as np
import pytest

from ntl_engine.graph.build import (
    GridGraph,
    add_node_with_type,
    add_edge_with_attr,
    build_incidence_matrix,
    get_branch_attributes,
)
from ntl_engine.domain.types import NodeType


def test_incidence_matrix_kcl() -> None:
    """A @ i = 0 for a 3-node loop (a->b->c->a); nonzero currents satisfy KCL."""
    import networkx as nx
    G: GridGraph = nx.DiGraph()
    add_node_with_type(G, "a", NodeType.TRANSFORMER)
    add_node_with_type(G, "b", NodeType.JUNCTION)
    add_node_with_type(G, "c", NodeType.SMART_METER)
    add_edge_with_attr(G, "a", "b", R=0.1, X=0.02, Max_Capacity=100.0)
    add_edge_with_attr(G, "b", "c", R=0.1, X=0.02, Max_Capacity=100.0)
    add_edge_with_attr(G, "c", "a", R=0.1, X=0.02, Max_Capacity=100.0)

    A, nodes, edges = build_incidence_matrix(G, reference_node="a")
    assert A.shape[0] == 2  # 3 nodes - 1 ref
    assert A.shape[1] == 3  # 3 edges

    # In a loop, KCL allows equal current in all branches: i = [1.0, 1.0, 1.0]
    i = np.array([1.0, 1.0, 1.0])
    violation = A @ i
    np.testing.assert_allclose(violation, 0.0, atol=1e-10)


def test_get_branch_attributes() -> None:
    """Branch attributes returned in edge order."""
    import networkx as nx
    G: GridGraph = nx.DiGraph()
    add_node_with_type(G, "a", NodeType.TRANSFORMER)
    add_node_with_type(G, "b", NodeType.SMART_METER)
    add_edge_with_attr(G, "a", "b", R=0.5, X=0.1, Max_Capacity=50.0)
    edges = list(G.edges())
    R, X, MaxCap = get_branch_attributes(G, edges)
    assert len(R) == 1
    assert R[0] == 0.5
    assert X[0] == 0.1
    assert MaxCap[0] == 50.0
