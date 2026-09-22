from typing import Protocol

from clip_engine_worker.noop import run_noop_job


class NoopActor(Protocol):
    def send(self, message: str) -> object: ...


def enqueue_noop_job(
    message: str = "compose-smoke",
    actor: NoopActor = run_noop_job,
) -> object:
    return actor.send(message)


if __name__ == "__main__":
    enqueue_noop_job()
