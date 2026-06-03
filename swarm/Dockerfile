FROM python:3.11-slim

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

RUN pip install --no-cache-dir httpx pydantic fastapi uvicorn websockets structlog

COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Drop all capabilities at runtime (docker run --cap-drop=ALL)
# If using Docker Compose, add: cap_drop: [ALL]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
