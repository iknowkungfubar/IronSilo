FROM python:3.11-slim

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Install base dependencies only
RUN pip install --no-cache-dir \
    uvicorn==0.27.0 \
    fastapi==0.109.0 \
    pydantic==2.6.1 \
    structlog==24.1.0 \
    httpx==0.25.2

# Copy fallback API with proper ownership
COPY --chown=appuser:appuser app.py ./

# Create cache directory with proper permissions
RUN mkdir -p /app/cache && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the API
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the API
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
