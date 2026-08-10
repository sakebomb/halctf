# --- Builder stage: has the toolchain only to compile pycosat (no wheel exists) ---
FROM python:3.11-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install into an isolated prefix so we can copy just the packages, not gcc.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Final stage: slim runtime, no compiler (saves ~230 MB in the shipped tar) ---
FROM python:3.11-slim-bookworm

# Copy the compiled/installed packages from the builder.
COPY --from=builder /install /usr/local

# Copy agent code
COPY main.py ./agent/main.py
COPY mcp_client.py ./agent/mcp_client.py
COPY solvers ./agent/solvers
RUN chmod +x ./agent/main.py

# Set Python path for module imports
ENV PYTHONPATH=/agent

# Unbuffered Python output (critical for heartbeat)
ENTRYPOINT ["python", "-u", "/agent/main.py"]
