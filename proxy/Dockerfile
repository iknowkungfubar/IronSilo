FROM python:3.11-slim

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy all Python files in the proxy module
COPY --chown=appuser:appuser proxy.py models.py classifier.py config.yaml ./

# Install PyTorch (CPU-only) and standard packages
RUN pip install --no-cache-dir \
    torch==2.1.2 \
    torchvision==0.16.2 \
    torchaudio==2.1.2 \
    --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn==0.27.0 \
    httpx==0.25.2 \
    pydantic==2.6.1 \
    pydantic-settings==2.1.0 \
    structlog==24.1.0 && \
    pip install --no-cache-dir llmlingua==0.2.0 || echo "LLMLingua optional - compression disabled if unavailable"

# Create __init__.py to make it a package
RUN touch __init__.py

# Create directory for cache persistence with proper permissions
RUN mkdir -p /app/cache && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "proxy:app", "--host", "0.0.0.0", "--port", "8001"]
