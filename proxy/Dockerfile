FROM python:3.11-slim
WORKDIR /app

# Copy all Python files in the proxy module
COPY proxy.py models.py classifier.py config.yaml ./

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

CMD ["uvicorn", "proxy:app", "--host", "0.0.0.0", "--port", "8001"]
