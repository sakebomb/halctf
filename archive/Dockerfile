# HalCTF Autonomous Agent - Optimized for size and security
FROM python:3.12-slim

# Install essential CTF tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    netcat-openbsd \
    nmap \
    dnsutils \
    iputils-ping \
    vim-tiny \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 ctfuser

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agent.py .

# Set ownership
RUN chown -R ctfuser:ctfuser /app

# Switch to non-root user
USER ctfuser

# Make agent executable
RUN chmod +x agent.py

# Run agent
CMD ["python3", "-u", "agent.py"]
