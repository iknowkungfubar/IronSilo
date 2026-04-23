FROM python:3.11-slim
WORKDIR /app

# Install Genesys with PostgreSQL and Local Embedding support
RUN pip install --no-cache-dir 'genesys-memory[postgres,local]'

# Expose the API and MCP server
EXPOSE 8000

# Start the Genesys server
CMD ["uvicorn", "genesys.api:app", "--host", "0.0.0.0", "--port", "8000"]