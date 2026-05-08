from app.workers.celery_app import celery_app


@celery_app.task(name="ingest.log_blob")
def ingest_log_blob(blob_id: str) -> dict:
    """Placeholder Celery task for log/doc ingestion."""

    return {"blob_id": blob_id, "status": "queued"}
