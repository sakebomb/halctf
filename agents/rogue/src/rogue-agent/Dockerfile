# HAL-format CTF agent — lightweight single-stage image.
# All deps ship prebuilt wheels, so NO compiler/toolchain is needed (keeps the
# shipped .tar small, ~140-170 MB).
#
# If a dependency has NO wheel (e.g. pycosat), switch to a multi-stage build:
#   FROM python:3.11-slim-bookworm AS builder
#   RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev \
#       && rm -rf /var/lib/apt/lists/*
#   COPY requirements.txt .
#   RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
#   FROM python:3.11-slim-bookworm
#   COPY --from=builder /install /usr/local
#   ... (then the COPY/ENV/ENTRYPOINT below)
# If a solver needs a runtime binary tool (pwntools' nm/objdump), add ONLY
# `binutils` to the final stage — never gcc/g++/make (~230 MB dead weight).

FROM python:3.11-slim-bookworm

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./agent/main.py
COPY llm.py ./agent/llm.py
COPY mcp_client.py ./agent/mcp_client.py
COPY solvers ./agent/solvers
RUN chmod +x ./agent/main.py

# Module imports resolve from /agent
ENV PYTHONPATH=/agent

# Unbuffered output is CRITICAL — the platform reads stdout as a heartbeat.
ENTRYPOINT ["python", "-u", "/agent/main.py"]
