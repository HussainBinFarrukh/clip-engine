import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.services.llm_provider import LLMProvider, LLMUsage
from tests.conftest import FIXTURE_VIDEO, skip_if_transient_llm_outage


class _FakeScoringProvider(LLMProvider):
    name = "fake"
    model = "fake-model"

    def __init__(self, score: int = 80) -> None:
        self._score = score
        self.calls = 0

    def generate(self, prompt: str) -> tuple[str, LLMUsage]:
        self.calls += 1
        payload = {
            "hook_line": True,
            "self_contained": True,
            "emotional_peak": False,
            "quotable_line": "A quotable line.",
            "score": self._score,
            "reason": "A solid, self-contained moment with a strong opener.",
        }
        return json.dumps(payload), LLMUsage(input_tokens=50, output_tokens=20, cost_usd=0.0001)


def _pipeline_up_to_signals(client: TestClient) -> tuple[str, str]:
    project_id = client.post("/projects", json={"name": "Scoring Project"}).json()["id"]
    source = client.post(
        f"/projects/{project_id}/sources",
        json={"title": "Fixture", "source_kind": "local_upload"},
    ).json()
    with FIXTURE_VIDEO.open("rb") as fixture_file:
        client.post(
            f"/projects/{project_id}/sources/{source['id']}/upload",
            files={"file": ("speech_45s.mp4", fixture_file, "video/mp4")},
        )
    client.post(f"/projects/{project_id}/sources/{source['id']}/transcribe")
    client.post(f"/projects/{project_id}/sources/{source['id']}/extract-signals")
    return project_id, source["id"]


def test_score_candidates_persists_ranked_candidates_with_reasons(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.services.jobs.get_llm_provider", lambda: _FakeScoringProvider())
    project_id, source_id = _pipeline_up_to_signals(client)

    response = client.post(f"/projects/{project_id}/sources/{source_id}/score-candidates")
    assert response.status_code == 200
    # Returns before the job runs, same contract as every other stage.
    assert response.json()["status"] == "ready"

    candidates = client.get(f"/projects/{project_id}/sources/{source_id}/candidates").json()
    assert len(candidates) > 0

    for candidate in candidates:
        assert candidate["reason"]
        assert candidate["preset"] == "shorts_campaign"  # only preset the fixture can reach
        assert 0 <= candidate["llm_score"] <= 100
        assert candidate["prompt_version"] == 1
        assert "avg_loudness_dbfs" in candidate["feature_vector"]

    scores = [c["combined_score"] for c in candidates]
    assert scores == sorted(scores, reverse=True)  # ranked, best first


def test_rescoring_same_prompt_version_replaces_candidates(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.services.jobs.get_llm_provider", lambda: _FakeScoringProvider())
    project_id, source_id = _pipeline_up_to_signals(client)

    client.post(f"/projects/{project_id}/sources/{source_id}/score-candidates")
    first_count = len(
        client.get(f"/projects/{project_id}/sources/{source_id}/candidates").json()
    )

    client.post(f"/projects/{project_id}/sources/{source_id}/score-candidates")
    second_count = len(
        client.get(f"/projects/{project_id}/sources/{source_id}/candidates").json()
    )

    assert first_count > 0
    assert second_count == first_count  # replaced, not duplicated


def test_rescoring_with_new_prompt_version_keeps_old_results(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.services.jobs.get_llm_provider", lambda: _FakeScoringProvider())
    project_id, source_id = _pipeline_up_to_signals(client)

    client.post(
        f"/projects/{project_id}/sources/{source_id}/score-candidates",
        json={"prompt_version": 1},
    )
    v1_candidates = client.get(f"/projects/{project_id}/sources/{source_id}/candidates").json()

    client.post(
        f"/projects/{project_id}/sources/{source_id}/score-candidates",
        json={"prompt_version": 2},
    )
    all_candidates = client.get(f"/projects/{project_id}/sources/{source_id}/candidates").json()

    v1_still_present = [c for c in all_candidates if c["prompt_version"] == 1]
    v2_present = [c for c in all_candidates if c["prompt_version"] == 2]

    assert len(v1_still_present) == len(v1_candidates)
    assert len(v2_present) > 0
    assert len(all_candidates) == len(v1_still_present) + len(v2_present)


def test_score_candidates_rejects_without_signals(client: TestClient) -> None:
    project_id = client.post("/projects", json={"name": "No Signals"}).json()["id"]
    source = client.post(
        f"/projects/{project_id}/sources",
        json={"title": "Fixture", "source_kind": "local_upload"},
    ).json()
    with FIXTURE_VIDEO.open("rb") as fixture_file:
        client.post(
            f"/projects/{project_id}/sources/{source['id']}/upload",
            files={"file": ("speech_45s.mp4", fixture_file, "video/mp4")},
        )
    client.post(f"/projects/{project_id}/sources/{source['id']}/transcribe")

    response = client.post(f"/projects/{project_id}/sources/{source['id']}/score-candidates")

    assert response.status_code == 400


def test_score_candidates_rejects_when_not_ready(client: TestClient) -> None:
    project_id = client.post("/projects", json={"name": "Draft"}).json()["id"]
    source = client.post(
        f"/projects/{project_id}/sources",
        json={"title": "Draft", "source_kind": "local_upload"},
    ).json()

    response = client.post(f"/projects/{project_id}/sources/{source['id']}/score-candidates")

    assert response.status_code == 400


@pytest.mark.skipif(not settings.gemini_api_key, reason="no GEMINI_API_KEY configured")
def test_real_scoring_produces_plausible_ranked_candidates(client: TestClient) -> None:
    project_id, source_id = _pipeline_up_to_signals(client)

    response = client.post(f"/projects/{project_id}/sources/{source_id}/score-candidates")
    assert response.status_code == 200

    candidates = client.get(f"/projects/{project_id}/sources/{source_id}/candidates").json()

    if len(candidates) == 0:
        # The job ran synchronously and may have failed; dispatch swallows
        # the exception into the Job row rather than raising it here, so
        # check *that* for a transient-outage signature before failing.
        jobs = client.get(f"/projects/{project_id}/jobs").json()
        scoring_job = next(j for j in jobs if j["stage"] == "candidate_scoring")
        skip_if_transient_llm_outage(RuntimeError(scoring_job.get("error_message") or ""))

    assert len(candidates) > 0

    for candidate in candidates:
        assert isinstance(candidate["reason"], str) and len(candidate["reason"]) > 0
        assert 0 <= candidate["llm_score"] <= 100
        assert candidate["model"]  # a real Gemini model name, not empty
