"""Physics-Informed ML loss: KCL, Ohm's Law, I²R (vectorized PyTorch)."""

from ntl_engine.physics.loss import (
    piml_loss,
    kcl_loss,
    ohm_loss,
    technical_loss_vectorized,
)

__all__ = [
    "piml_loss",
    "kcl_loss",
    "ohm_loss",
    "technical_loss_vectorized",
]
