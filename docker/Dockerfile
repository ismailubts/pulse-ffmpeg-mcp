# FFMPEG MCP Server - Application Layer
# Uses minimal Ubuntu base with Python + Java + FFmpeg

FROM ffmpeg-mcp-ubuntu-base:latest

# Copy application code
COPY pyproject.toml /app/
COPY src/ /app/src/
COPY tests/ /app/tests/

# Install Python dependencies
RUN python3 -m pip install --no-cache-dir .

# Expose MCP server port
EXPOSE 8000

# Health check for MCP server
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s \
    CMD curl -f http://localhost:8000/health || exit 1

# Run MCP server
CMD ["python3", "-m", "src.server"]