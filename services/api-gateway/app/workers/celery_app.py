from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "aegisops",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.autodiscover_tasks(["app.workers.tasks"])
