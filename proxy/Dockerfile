FROM python:3.11-slim
WORKDIR /app
COPY proxy.py .

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
    llmlingua==0.2.0

CMD ["uvicorn", "proxy:app", "--host", "0.0.0.0", "--port", "8001"]
