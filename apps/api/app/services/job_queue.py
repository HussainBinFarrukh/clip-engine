import os
import uuid

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker

from app.core.config import settings


def _configure_broker() -> dramatiq.Broker:
    if os.getenv("DRAMATIQ_BROKER") == "stub":
        broker = StubBroker()
        dramatiq.set_broker(broker)
        return broker

    broker = RedisBroker(url=settings.redis_url)
    dramatiq.set_broker(broker)
    return broker


broker = _configure_broker()


@dramatiq.actor(broker=broker, queue_name="jobs", max_retries=0)
def run_job_stage(job_id: str) -> None:
    """Declared here so the API process can enqueue messages onto the
    "jobs" queue. The worker process (workers/clip_engine_worker/jobs.py)
    registers the actor that actually executes the stage — dramatiq only
    needs the actor name and queue to match between the two processes.
    Retries are handled explicitly via the /jobs/{id}/retry endpoint,
    not dramatiq's own retry machinery, hence max_retries=0.
    """
    raise NotImplementedError("run_job_stage executes in the worker process")


def dispatch_job(job_id: uuid.UUID) -> None:
    run_job_stage.send(str(job_id))
