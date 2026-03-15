"""Unit tests for data simulator: physics consistency."""

import sys
from pathlib import Path

import numpy as np
import pytest

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "src"))

from ntl_engine.graph.build import build_incidence_matrix
from ntl_engine.simulator.grid import build_simple_feeder, solve_dc_power_flow


def test_simulator_build_feeder() -> None:
    """Simulator's build_simple_feeder produces valid graph."""
    G, meter_ids = build_simple_feeder(5)
    assert len(meter_ids) == 5
    assert G.number_of_nodes() == 1 + 5 + 5  # trans + junctions + meters
    assert G.number_of_edges() == 10  # trans->j, j->m each


def test_simulator_power_flow_kcl() -> None:
    """Solve_dc_power_flow: at junction nodes KCL holds (inflow = outflow).
    Meter nodes are loads (current sinks), so full A @ i = 0 would wrongly force
    meter currents to zero. We only assert KCL at junction nodes."""
    G, meter_ids = build_simple_feeder(3)
    P_demand = [100.0, 200.0, 150.0]
    V, I, P, I_branch = solve_dc_power_flow(G, meter_ids, P_demand)
    # Solver returns I_branch in sorted(G.edges()) order; use same for A
    edges = sorted(G.edges())
    A, nodes_without_ref, edges_A = build_incidence_matrix(G, branch_order=edges)
    assert edges_A == edges
    i_vec = np.array(I_branch, dtype=np.float64)
    junction_rows = [i for i, n in enumerate(nodes_without_ref) if n.startswith("j")]
    A_junction = A[junction_rows, :]
    violation = A_junction @ i_vec
    # Single-pass DC flow does not iterate to convergence; allow small residual
    np.testing.assert_allclose(violation, 0.0, atol=1e-2)
