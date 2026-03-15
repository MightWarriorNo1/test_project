"""
Grid simulator: build radial feeder, solve DC power flow (KCL + Ohm), generate timesteps with fraud.
"""

import random
from datetime import datetime
from typing import List, Optional, Tuple

from ntl_engine.domain.types import NodeType
from ntl_engine.graph.build import (
    GridGraph,
    add_node_with_type,
    add_edge_with_attr,
)


def build_simple_feeder(
    num_meters: int,
    R_per_meter: float = 0.1,
    X_per_meter: float = 0.02,
    max_capacity: float = 100.0,
) -> Tuple[GridGraph, List[str]]:
    """
    Build a radial feeder: trans -> ji -> mi for each i. Star topology.
    """
    import networkx as nx
    G: GridGraph = nx.DiGraph()
    add_node_with_type(G, "trans", NodeType.TRANSFORMER)
    meter_ids: List[str] = []
    for i in range(num_meters):
        jid = f"j{i}"
        mid = f"m{i}"
        add_node_with_type(G, jid, NodeType.JUNCTION)
        add_node_with_type(G, mid, NodeType.SMART_METER)
        add_edge_with_attr(G, "trans", jid, R=R_per_meter, X=X_per_meter, Max_Capacity=max_capacity)
        add_edge_with_attr(G, jid, mid, R=R_per_meter * 0.5, X=X_per_meter * 0.5, Max_Capacity=max_capacity)
        meter_ids.append(mid)
    return G, meter_ids


def solve_dc_power_flow(
    G: GridGraph,
    meter_ids: List[str],
    P_demand_per_meter: List[float],
    V_source: float = 127.0,
) -> Tuple[List[float], List[float], List[float], List[float]]:
    """
    Simplified DC flow: P = V*I, V_drop = I*R. Returns (V_meters, I_meters, P_meters, I_branch).
    I_branch is in canonical (sorted) edge order so it aligns with build_incidence_matrix(G, branch_order=sorted(G.edges())).
    """
    edges = sorted(G.edges())
    n_edges = len(edges)
    node_to_meter = {mid: i for i, mid in enumerate(meter_ids)}
    R_list = [G.edges[e]["R"] for e in edges]

    V_meters = [V_source] * len(meter_ids)
    P_meters = list(P_demand_per_meter)
    I_meters = [P_meters[k] / V_meters[k] if V_meters[k] > 1e-6 else 0.0 for k in range(len(meter_ids))]

    I_branch = [0.0] * n_edges
    for idx, (u, v) in enumerate(edges):
        if v in node_to_meter:
            I_branch[idx] = I_meters[node_to_meter[v]]
    for idx, (u, v) in enumerate(edges):
        if v not in node_to_meter:
            for idx2, (u2, v2) in enumerate(edges):
                if u2 == v:
                    I_branch[idx] += I_branch[idx2]

    for i, mid in enumerate(meter_ids):
        path_edges = []
        current = mid
        while current != "trans":
            for (u, v) in edges:
                if v == current:
                    path_edges.append((u, v))
                    current = u
                    break
            else:
                break
        v_drop = 0.0
        for (u, v) in reversed(path_edges):
            e = (u, v)
            ie = edges.index(e)
            v_drop += I_branch[ie] * R_list[ie]
        V_meters[i] = V_source - v_drop

    for k in range(len(meter_ids)):
        if V_meters[k] > 1e-6:
            I_meters[k] = P_meters[k] / V_meters[k]
        else:
            I_meters[k] = 0.0
    for idx, (u, v) in enumerate(edges):
        if v in node_to_meter:
            I_branch[idx] = I_meters[node_to_meter[v]]
    # Re-update junction upstream currents so KCL holds at junctions
    for idx, (u, v) in enumerate(edges):
        if v not in node_to_meter:
            I_branch[idx] = 0.0
            for idx2, (u2, v2) in enumerate(edges):
                if u2 == v:
                    I_branch[idx] += I_branch[idx2]

    return V_meters, I_meters, P_meters, I_branch


def generate_timestep(
    G: GridGraph,
    meter_ids: List[str],
    ts: datetime,
    base_P: float = 500.0,
    noise: float = 0.1,
    fraud_meters: Optional[List[str]] = None,
    fraud_under_report: float = 0.5,
) -> List[dict]:
    """Generate one timestep; optionally under-report P for fraud meters."""
    n = len(meter_ids)
    P_demand = [max(0, base_P * (1 + random.gauss(0, noise))) for _ in range(n)]
    fraud_set = set(fraud_meters or [])

    V, I, P, _ = solve_dc_power_flow(G, meter_ids, P_demand)
    rows = []
    for i, mid in enumerate(meter_ids):
        is_fraud = mid in fraud_set
        P_reported = P[i] * (1 - fraud_under_report) if is_fraud else P[i]
        rows.append({
            "meter_id": mid,
            "V": round(V[i], 4),
            "I": round(I[i], 4),
            "P": round(P_reported, 4),
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "Is_Fraud": is_fraud,
        })
    return rows
