FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Install Python dependencies and the application
RUN pip install --no-cache-dir .

# Create directories for static assets
RUN mkdir -p static/models static/textures static/cabins static/thumbnails

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Use --workers 1 because InMemorySessionService doesn't support multi-process
# For production with many workers, switch to Redis-based session store
CMD ["uvicorn", "workflows.orchestrator:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
