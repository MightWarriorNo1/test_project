"""
GNN for per-meter anomaly scoring. MessagePassing (2–3 layers), node features V, I, P,
edge features R, X, Max_Capacity; per-node readout for anomaly score.
"""

from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import MessagePassing
from ntl_engine.graph.build import GridGraph, get_branch_attributes

if TYPE_CHECKING:
    pass


class EdgeConv(MessagePassing):
    """Simple edge-conv: message = edge_attr, aggregate = add."""

    def __init__(self, in_channels: int, edge_dim: int, out_channels: int) -> None:
        super().__init__(aggr="add")
        self.lin = nn.Linear(in_channels + edge_dim, out_channels)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
    ) -> torch.Tensor:
        return self.propagate(edge_index, x=x, edge_attr=edge_attr)

    def message(self, x_j: torch.Tensor, edge_attr: torch.Tensor) -> torch.Tensor:
        return self.lin(torch.cat([x_j, edge_attr], dim=-1))


class MeterAnomalyGNN(nn.Module):
    """
    2-layer GNN with per-node anomaly score. Input: node features (V, I, P, ...), edge features (R, X, Max_Capacity).
    Output: anomaly score per node (logits or probability).
    """

    def __init__(
        self,
        in_channels: int = 3,
        edge_dim: int = 3,
        hidden: int = 64,
        out_channels: int = 1,
        num_layers: int = 2,
    ) -> None:
        super().__init__()
        self.conv1 = EdgeConv(in_channels, edge_dim, hidden)
        self.conv2 = EdgeConv(hidden, edge_dim, hidden)
        self.lin = nn.Linear(hidden, out_channels)
        self.num_layers = num_layers

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        batch: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        x: (n_nodes, in_channels), edge_index: (2, n_edges), edge_attr: (n_edges, edge_dim).
        Returns (n_nodes, 1) anomaly logits per node.
        """
        h = F.relu(self.conv1(x, edge_index, edge_attr))
        h = F.relu(self.conv2(h, edge_index, edge_attr))
        return self.lin(h)

    def predict_proba(self, logits: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(logits)


def build_pyg_data(
    node_ids: List[str],
    node_features: torch.Tensor,
    edge_index: torch.Tensor,
    edge_attr: torch.Tensor,
    node_id_to_idx: Optional[Dict[str, int]] = None,
) -> Data:
    """
    Build PyG Data from node list and edge list. node_features (n_nodes, F), edge_index (2, E), edge_attr (E, D).
    """
    if node_id_to_idx is None:
        node_id_to_idx = {n: i for i, n in enumerate(node_ids)}
    return Data(
        x=node_features,
        edge_index=edge_index,
        edge_attr=edge_attr,
        node_ids=node_ids,
        node_id_to_idx=node_id_to_idx,
    )


def graph_from_readings(
    meter_readings: Dict[str, Dict[str, float]],
    G: GridGraph,
    node_id_to_idx: Dict[str, int],
    default_V: float = 127.0,
    default_I: float = 0.0,
    default_P: float = 0.0,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Build node feature matrix and edge index/attr from window snapshot and grid graph.
    Returns (x, edge_index, edge_attr) for PyG. Node order must match node_id_to_idx.
    """
    nodes = sorted(node_id_to_idx.keys(), key=lambda n: node_id_to_idx[n])
    n = len(nodes)
    # Node features: V, I, P (3). Use defaults for non-meters.
    F_node = 3
    x = torch.zeros(n, F_node)
    for i, node_id in enumerate(nodes):
        r = meter_readings.get(node_id, {})
        x[i, 0] = r.get("V_avg", default_V)
        x[i, 1] = r.get("I_avg", default_I)
        x[i, 2] = r.get("P_sum", default_P)  # or P_avg depending on aggregation

    edges = list(G.edges())
    if not edges:
        edge_index = torch.zeros(2, 0, dtype=torch.long)
        edge_attr = torch.zeros(0, 3)
        return x, edge_index, edge_attr

    edge_index = torch.tensor(
        [[node_id_to_idx[u], node_id_to_idx[v]] for u, v in edges],
        dtype=torch.long,
    ).T
    R, X, MaxCap = get_branch_attributes(G, edges)
    edge_attr = torch.tensor(
        [[R[i], X[i], MaxCap[i]] for i in range(len(edges))],
        dtype=torch.get_default_dtype(),
    )
    return x, edge_index, edge_attr
