FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default environment
ENV APP_ENV=production
ENV LOG_LEVEL=INFO
ENV LOG_FORMAT=json

EXPOSE 8000

# Render (and most PaaS providers) inject a PORT env var (10000 on Render free)
# and route traffic to it, so bind to $PORT and fall back to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
