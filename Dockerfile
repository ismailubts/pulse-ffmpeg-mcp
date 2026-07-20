# FFMPEG MCP Server - Stock Ubuntu image for minimal build time
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies using stock Ubuntu packages (faster, cached)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    mediainfo \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ALPINE CONFIG MOVED ASIDE - uncomment if needed later
# FROM python:3.13-alpine
# RUN apk add --no-cache bash curl ffmpeg openjdk11-jre libsndfile-dev python3-dev gcc musl-dev

# Standard pip for production simplicity (no UV dependency)
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Create working directory
WORKDIR /app

# Create non-root user (Ubuntu syntax)
RUN groupadd -g 1000 mcp && useradd -u 1000 -g mcp -m -s /bin/bash mcp

# Create directories for file processing with proper permissions
RUN mkdir -p /tmp/music/{source,temp,screenshots,metadata,finished} \
    && chown -R mcp:mcp /app /tmp/music

# Copy application code
COPY src/ ./src/
COPY tests/ ./tests/
COPY README.md ./

# Set Python path for module imports  
ENV PYTHONPATH=/app

# Create health check script
RUN echo '#!/bin/bash\npython -c "import src.server; print(\"✅ MCP server OK\")" || exit 1' > /app/healthcheck.sh \
    && chmod +x /app/healthcheck.sh \
    && chown -R mcp:mcp /app

# Test that critical tools work
RUN ffmpeg -version > /dev/null 2>&1 && \
    java -version > /dev/null 2>&1 && \
    python -c "import psutil; print('Python OK')" && \
    echo "✅ Minimal production image validation passed"

# Switch to non-root user
USER mcp

# Expose MCP server port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh

# Default command
CMD ["python", "-m", "src.server"]

# Labels
LABEL maintainer="ismailubts" \
      version="1.0.0-minimal" \
      description="FFMPEG MCP Server - Minimal Alpine Build (FFMPEG + Java + Python only)"