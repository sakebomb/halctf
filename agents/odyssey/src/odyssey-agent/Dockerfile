FROM python:3.11-slim-bookworm

# Copy and install Python dependencies (pure Python, no compilation needed)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY main.py ./agent/main.py
COPY mcp_client.py ./agent/mcp_client.py
COPY solvers ./agent/solvers

# Set Python path for module imports
ENV PYTHONPATH=/agent

# Unbuffered Python output (critical for heartbeat)
ENTRYPOINT ["python", "-u", "/agent/main.py"]
