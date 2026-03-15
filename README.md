# NTL Detection Engine

Production-ready Non-Technical Loss (NTL) detection for power distribution grids using Physics-Informed ML (PIML) and Graph Neural Networks (GNN).

## Features

- **Heterogeneous grid graph**: Transformers, Junctions, SmartMeters; edges with R, X, Max_Capacity
- **Kafka-based ingestion**: Sliding window with late-arriving and out-of-order event handling
- **PIML loss**: KCL, Ohm's Law, and I²R technical loss (vectorized, PyTorch)
- **GNN anomaly detection**: Per-meter anomaly scores with XAI reason codes (Integrated Gradients)
- **Data simulator**: Physically consistent power flow data with synthetic fraud labels
- **Docker Compose**: Kafka, TimescaleDB, Redis, FastAPI, Celery worker

## Quick start

```bash
# Install
pip install -e .

# Generate training data
python scripts/simulate_grid_data.py --output data/simulated --num-meters 50 --fraud-rate 0.1

# Run tests
pytest

# Run stack (requires Docker)
docker compose up -d
```

## Troubleshooting

- **Docker:** If you see `failed to connect to the docker API` or `dockerDesktopLinuxEngine`, start **Docker Desktop** and wait until it reports "Docker Desktop is running", then run `docker compose up -d` again.
- **pip install:** If you get `WinError 32` (file in use) during install, close other terminals/IDEs, delete any `ntl_detection_engine.egg-info` folder in the project, then run `pip install .` (non-editable).

## Project layout

- `src/config/` — Configuration and physical constants
- `src/domain/` — Domain types (NodeType, Telemetry, etc.)
- `src/graph/` — Graph build and incidence matrix
- `src/ingestion/` — Kafka consumer, sliding window, validator
- `src/physics/` — PIML loss functions
- `src/models/` — GNN anomaly model
- `src/xai/` — Explainability (Integrated Gradients, reason codes)
- `src/api/` — FastAPI inference API
- `src/workers/` — Async inference worker (Celery)
- `scripts/simulate_grid_data.py` — Data simulator

## Units

Internal units: V (Volts), I (Amperes), P (Watts), R/X (Ohms). Conversion from kW/kΩ at ingestion.
