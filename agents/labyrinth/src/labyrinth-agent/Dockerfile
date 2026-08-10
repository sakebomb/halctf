FROM python:3.11-slim-bookworm

# Only binutils is needed at runtime (nm/objdump for the Achilles pwn solver).
# The gcc/g++/make/dev headers were dead weight — pwntools ships wheels — and
# dropping them saves ~230 MB off the image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY main.py ./agent/main.py
COPY llm.py ./agent/llm.py
COPY mcp_client.py ./agent/mcp_client.py
COPY solvers ./agent/solvers
# Bundled challenge attachments (achilles_heel binary, gatekeeper_stage1.py) that
# the pod cannot fetch at runtime — the human drops them in before build.
COPY attachments ./agent/attachments
RUN chmod +x ./agent/main.py

# Set Python path for module imports
ENV PYTHONPATH=/agent

# Unbuffered Python output (critical for heartbeat)
ENTRYPOINT ["python", "-u", "/agent/main.py"]
