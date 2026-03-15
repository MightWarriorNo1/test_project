FROM python:3.10-slim

WORKDIR /app

# Install system deps if needed (e.g. for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY src/ ./src/
COPY scripts/ ./scripts/

ENV PYTHONPATH=/app/src
WORKDIR /app

# Default: run API
CMD ["uvicorn", "ntl_engine.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
