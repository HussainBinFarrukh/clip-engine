import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.job import JobStage, JobState
from app.services.jobs import enqueue_job, execute_job


def test_failing_test_stage_then_retry_succeeds(db_session: Session) -> None:
    job = enqueue_job(
        db_session,
        stage=JobStage.TEST_STAGE,
        input_json={"should_fail": True, "fail_attempts": 1, "failure_message": "boom"},
    )

    failed = execute_job(db_session, job.id)
    assert failed.state == JobState.FAILED
    assert failed.attempts == 1
    assert failed.error_message == "boom"
    assert failed.error_code == "TestStageFailure"

    # Simulate the retry endpoint: reset to queued, then run again. The
    # stage only fails for the first `fail_attempts` attempts, so the
    # second attempt succeeds.
    failed.state = JobState.QUEUED
    db_session.commit()

    retried = execute_job(db_session, job.id)
    assert retried.state == JobState.COMPLETED
    assert retried.attempts == 2
    assert retried.error_message is None
    assert retried.output_json == {"ok": True}


def test_retry_endpoint_reruns_a_failed_job(client: TestClient, db_session: Session) -> None:
    job = enqueue_job(
        db_session,
        stage=JobStage.TEST_STAGE,
        input_json={"should_fail": True, "fail_attempts": 1},
    )
    execute_job(db_session, job.id)

    failed = client.get(f"/jobs/{job.id}").json()
    assert failed["state"] == "failed"

    retried = client.post(f"/jobs/{job.id}/retry")
    assert retried.status_code == 200
    assert retried.json()["state"] == "completed"
    assert retried.json()["attempts"] == 2


def test_retry_rejects_a_job_that_is_not_failed(client: TestClient, db_session: Session) -> None:
    job = enqueue_job(db_session, stage=JobStage.TEST_STAGE, input_json={"should_fail": False})

    response = client.post(f"/jobs/{job.id}/retry")

    assert response.status_code == 400


def test_get_job_returns_404_when_missing(client: TestClient) -> None:
    response = client.get(f"/jobs/{uuid.uuid4()}")
    assert response.status_code == 404
