import uuid

import dramatiq
from app.db.session import SessionLocal
from app.services.jobs import execute_job

from clip_engine_worker.broker import broker


@dramatiq.actor(broker=broker, queue_name="jobs", max_retries=0)
def run_job_stage(job_id: str) -> None:
    db = SessionLocal()
    try:
        execute_job(db, uuid.UUID(job_id))
    finally:
        db.close()
