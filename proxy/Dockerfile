FROM python:3.13-slim

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

COPY --chown=appuser:appuser proxy.py models.py classifier.py config.yaml ./

# Install only what's actually needed — no torch/llmlingua (removed Phase 1)
RUN pip install --no-cache-dir \
    fastapi>=0.109.0 \
    uvicorn>=0.27.0 \
    httpx>=0.25.2 \
    pydantic>=2.6.1 \
    pydantic-settings>=2.1.0 \
    structlog>=24.1.0 \
    headroom-ai[all]>=0.25.0

RUN touch __init__.py
RUN mkdir -p /app/cache && chown -R appuser:appuser /app

USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "proxy:app", "--host", "0.0.0.0", "--port", "8001"]
