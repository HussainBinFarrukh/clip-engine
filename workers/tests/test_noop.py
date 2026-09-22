from clip_engine_worker.enqueue_noop import enqueue_noop_job
from clip_engine_worker.noop import perform_noop_job, run_noop_job


class FakeNoopActor:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, message: str) -> dict[str, str]:
        self.messages.append(message)
        return {"queued": message}


def test_noop_actor_declared() -> None:
    assert run_noop_job.actor_name == "run_noop_job"
    assert run_noop_job.queue_name == "default"


def test_noop_job_runs() -> None:
    assert perform_noop_job("smoke") == {"status": "completed", "message": "smoke"}


def test_enqueue_noop_job_sends_actor_message() -> None:
    actor = FakeNoopActor()

    result = enqueue_noop_job("compose-smoke", actor=actor)

    assert result == {"queued": "compose-smoke"}
    assert actor.messages == ["compose-smoke"]
