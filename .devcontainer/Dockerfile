FROM mcr.microsoft.com/devcontainers/python:3.11

# Install additional system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    postgresql-client \
    build-essential \
    libpq-dev \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Install Node.js 18.x
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest

# Set working directory
WORKDIR /workspace

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install development dependencies
RUN pip install --no-cache-dir \
    black \
    isort \
    mypy \
    pytest \
    pytest-asyncio \
    pytest-cov \
    httpx

# Create necessary directories
RUN mkdir -p /workspace/artifacts /workspace/temp /workspace/logs \
    && chmod 755 /workspace/artifacts /workspace/temp /workspace/logs

# Switch to vscode user
USER vscode
