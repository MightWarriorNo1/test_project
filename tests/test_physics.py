"""Unit tests for PIML loss: KCL, Ohm, I²R."""

import pytest
torch = pytest.importorskip("torch")

from ntl_engine.physics.loss import (
    kcl_loss,
    ohm_loss,
    technical_loss_vectorized,
    piml_loss,
)


def test_kcl_loss_zero_when_satisfied() -> None:
    """When A @ i = 0, KCL loss should be zero."""
    A = torch.tensor([[1.0, -1.0]], dtype=torch.float32)  # 1 node (without ref), 2 edges: i1 - i2 = 0
    i = torch.tensor([1.0, 1.0], dtype=torch.float32)
    loss = kcl_loss(A, i)
    assert loss.item() < 1e-6


def test_kcl_loss_positive_when_violated() -> None:
    """When A @ i != 0, KCL loss > 0."""
    A = torch.tensor([[1.0, -1.0]], dtype=torch.float32)
    i = torch.tensor([1.0, 2.0], dtype=torch.float32)
    loss = kcl_loss(A, i)
    assert loss.item() > 0.5


def test_technical_loss_vectorized() -> None:
    """I²R sum: two branches I=[2,3], R=[1,1] -> 4+9=13."""
    I = torch.tensor([2.0, 3.0], dtype=torch.float32)
    R = torch.tensor([1.0, 1.0], dtype=torch.float32)
    loss = technical_loss_vectorized(I, R)
    assert abs(loss.item() - 13.0) < 1e-5


def test_ohm_loss() -> None:
    """V_drop = I*Z -> loss zero when V_drop_observed = I*Z."""
    V = torch.tensor([10.0, 20.0], dtype=torch.float32)
    I = torch.tensor([1.0, 2.0], dtype=torch.float32)
    Z = torch.tensor([10.0, 10.0], dtype=torch.float32)
    loss = ohm_loss(V, I, Z)
    assert loss.item() < 1e-5


def test_piml_combined() -> None:
    """Combined loss is sum of terms."""
    A = torch.tensor([[1.0, -1.0]], dtype=torch.float32)
    i = torch.tensor([1.0, 1.0], dtype=torch.float32, requires_grad=True)
    R = torch.tensor([0.1, 0.1], dtype=torch.float32)
    total = piml_loss(A, i, R, lambda_kcl=1.0, lambda_tech=0.01)
    assert total.dim() == 0
    assert total.requires_grad
