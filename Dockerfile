# Dockerfile.worker-llm - LLM Worker (Lightweight)
# No Playwright - just Python packages

FROM python:3.11-slim

WORKDIR /app

# Install only essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment
ENV PYTHONPATH=/app

# Health check - verify worker is running
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD celery -A celery_app inspect ping -d llm@$HOSTNAME || exit 1

# Start LLM worker (listens to 'celery' queue only)
CMD ["celery", "-A", "celery_app", "worker", \
     "--loglevel=info", \
     "--concurrency=10", \
     "-n", "llm@%h", \
     "-Q", "celery"]