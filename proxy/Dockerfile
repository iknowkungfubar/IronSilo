FROM python:3.11-slim
WORKDIR /app
COPY proxy.py .

# Step 1: Install PyTorch strictly from the CPU-only index
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Step 2: Install standard packages from the default PyPI index
RUN pip install --no-cache-dir fastapi uvicorn httpx llmlingua

CMD ["uvicorn", "proxy:app", "--host", "0.0.0.0", "--port", "8001"]