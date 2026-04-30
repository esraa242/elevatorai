FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y     build-essential     libpq-dev     && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Install Python dependencies and the application
RUN pip install --no-cache-dir .

# Create directories
RUN mkdir -p static/models static/textures

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "workflows.orchestrator:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
