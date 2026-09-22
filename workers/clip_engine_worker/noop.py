import dramatiq

from clip_engine_worker.broker import broker


def perform_noop_job(message: str = "ok") -> dict[str, str]:
    print(f"noop job: {message}", flush=True)
    return {"status": "completed", "message": message}


@dramatiq.actor(broker=broker, queue_name="default")
def run_noop_job(message: str = "ok") -> dict[str, str]:
    return perform_noop_job(message)
