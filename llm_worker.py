from celery import Celery
from config import config
# celery_app.py
import logging
import sys
from config import config

celery_app = Celery(
    "llm_worker",
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND,
    include=["tasks"]  # ← This imports tasks
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    worker_disable_rate_limits=True,
    worker_prefetch_multiplier=1,
    task_default_queue='llm_worker_queue'
)

celery_app.conf.task_routes = {
    "tasks.health_check": {"queue": "llm_worker_queue"},
}