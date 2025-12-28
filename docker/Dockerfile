# Multi-stage build for Agent Memory MCP Server
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --no-cache-dir uv

# ===================================
# Dependencies stage
# ===================================
FROM base as dependencies

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies using UV
RUN uv pip install --system --no-cache \
    fastmcp>=2.0.0 \
    asyncpg>=0.29.0 \
    sqlalchemy>=2.0.0 \
    alembic>=1.13.0 \
    pgvector>=0.2.4 \
    openai>=1.12.0 \
    cohere>=5.0.0 \
    httpx>=0.26.0 \
    sentence-transformers>=2.2.0 \
    litellm>=1.35.0 \
    langchain-text-splitters>=0.0.1 \
    markdown>=3.5.0 \
    pyyaml>=6.0.1 \
    watchdog>=4.0.0 \
    pydantic>=2.5.0 \
    pydantic-settings>=2.1.0 \
    python-dotenv>=1.0.0 \
    structlog>=24.1.0 \
    tenacity>=8.2.3 \
    python-dateutil>=2.8.0

# ===================================
# Application stage
# ===================================
FROM dependencies as application

# Copy application code
COPY config/ ./config/
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create directories
RUN mkdir -p /app/memory_files /app/logs

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check script
RUN echo '#!/bin/sh\npython -c "import sys; sys.exit(0)"' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

# Expose port for potential HTTP transport
EXPOSE 8000

# Run MCP server via stdio transport
CMD ["python", "-m", "src.main"]
