# Dockerfile.scraper - Scraper Worker
# Uses base image with all dependencies pre-installed

FROM umeshrajanna/deepship-scraper-base:latest

# Copy application code
COPY . .

# Expose no ports (worker doesn't need HTTP)

# Health check - verify worker can connect to Celery
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD celery -A workers.celery_app inspect ping -d scraper@$HOSTNAME || exit 1

# Start scraper worker
# Listens only to 'scraper_queue'
CMD ["celery", "-A", "workers.celery_app", "worker", \
     "--loglevel=info", \
     "--concurrency=2", \
     "-n", "scraper@%h", \
     "-Q", "scraper_queue"]