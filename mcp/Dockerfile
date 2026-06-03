FROM python:3.11-slim

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire mcp directory
COPY --chown=appuser:appuser . /app/

# Install MCP requirements
RUN pip install --no-cache-dir -r /app/requirements.txt

# Create cache directory with proper permissions
RUN mkdir -p /app/cache && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Entry point script
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["sh", "-c"]
# Default: run genesys server; override via MCP_SERVER_TYPE env var
CMD ["python -m uvicorn genesys_server:app --host 0.0.0.0 --port 8000"]
