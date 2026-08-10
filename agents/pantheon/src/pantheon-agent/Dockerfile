# --- Builder: toolchain ONLY to compile packages that lack a wheel ---
FROM python:3.11-slim-bookworm AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Final: slim runtime, no compiler (saves ~230 MB) ---
FROM python:3.11-slim-bookworm
# Add binutils for pwntools
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
COPY main.py ./agent/main.py
COPY mcp_client.py ./agent/mcp_client.py
COPY solvers ./agent/solvers
RUN chmod +x ./agent/main.py
ENV PYTHONPATH=/agent
# Unbuffered output is CRITICAL — the platform reads your stdout as a heartbeat.
ENTRYPOINT ["python", "-u", "/agent/main.py"]
