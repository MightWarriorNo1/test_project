"""
PIML loss: KCL (A @ i = 0), Ohm's Law (V_drop = I*Z), I²R technical loss.
Fully vectorized; O(n_edges) for technical loss, no iterative loops over nodes.
"""

from typing import Optional

import torch


def kcl_loss(A: torch.Tensor, i_branch: torch.Tensor) -> torch.Tensor:
    """
    Kirchhoff's Current Law: at each node sum of currents = 0.
    Vectorized form: A @ i = 0. Loss = ||A @ i||^2.
    A: (n_nodes-1, n_edges), i_branch: (n_edges,) or (batch, n_edges).
    """
    # (n_nodes-1,) or (batch, n_nodes-1)
    violation = torch.mv(A, i_branch) if i_branch.dim() == 1 else torch.matmul(i_branch, A.T)
    return (violation ** 2).sum()


def ohm_loss(
    V_drop_observed: torch.Tensor,
    I_branch: torch.Tensor,
    Z_branch: torch.Tensor,
    eps: float = 1e-6,
) -> torch.Tensor:
    """
    Ohm's Law: V_drop = I * Z (per branch). Resistive approximation: V_drop ≈ I*R.
    Loss = ||V_drop_observed - I * Z||^2. Z can be R (real) or |Z|.
    Clamp |I| and |Z| for numerical stability.
    """
    Z_safe = Z_branch.clamp(min=eps)
    I_safe = I_branch
    V_ohm = I_safe * Z_safe
    return ((V_drop_observed - V_ohm) ** 2).sum()


def technical_loss_vectorized(I_branch: torch.Tensor, R_branch: torch.Tensor) -> torch.Tensor:
    """
    Total technical loss = sum over branches of I_k^2 * R_k.
    Vectorized: (I_branch^2) * R_branch then sum. O(n_edges).
    """
    return (I_branch ** 2 * R_branch).sum()


def piml_loss(
    A: torch.Tensor,
    i_pred: torch.Tensor,
    R_branch: torch.Tensor,
    Z_branch: Optional[torch.Tensor] = None,
    V_drop_observed: Optional[torch.Tensor] = None,
    P_total_observed: Optional[torch.Tensor] = None,
    lambda_kcl: float = 1.0,
    lambda_ohm: float = 1.0,
    lambda_tech: float = 1.0,
    eps: float = 1e-6,
) -> torch.Tensor:
    """
    Combined PIML loss:
    L = lambda_kcl * L_KCL + lambda_ohm * L_Ohm + lambda_tech * L_tech (optional terms).
    If Z_branch and V_drop_observed are provided, L_Ohm is included.
    If P_total_observed is provided, L_tech term is |P_tech_total - P_total_observed| or MSE.
    """
    L_kcl = kcl_loss(A, i_pred)
    total = lambda_kcl * L_kcl

    if Z_branch is not None and V_drop_observed is not None:
        L_o = ohm_loss(V_drop_observed, i_pred, Z_branch, eps=eps)
        total = total + lambda_ohm * L_o

    P_tech = technical_loss_vectorized(i_pred, R_branch)
    if P_total_observed is not None:
        total = total + lambda_tech * (P_tech - P_total_observed).pow(2).sum()
    else:
        # Optional: just add small regularization on technical loss magnitude
        total = total + lambda_tech * 1e-4 * P_tech

    return total
