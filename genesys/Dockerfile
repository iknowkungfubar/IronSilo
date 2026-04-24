FROM python:3.11-slim
WORKDIR /app

# Install base dependencies only (no genesys-memory - using fallback API)
RUN pip install --no-cache-dir \
    uvicorn==0.27.0 \
    fastapi==0.109.0 \
    pydantic==2.6.1 \
    structlog==24.1.0 \
    httpx==0.25.2

# Copy fallback API
COPY app.py ./

# Expose the API
EXPOSE 8000

# Start the fallback API
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
