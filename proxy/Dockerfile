FROM python:3.11-slim
WORKDIR /app
COPY proxy.py .
RUN pip install --no-cache-dir fastapi uvicorn httpx llmlingua torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
CMD ["uvicorn", "proxy:app", "--host", "0.0.0.0", "--port", "8001"]
