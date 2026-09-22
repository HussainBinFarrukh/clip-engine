import json

import pytest
from fastapi.testclient import TestClient

from app.services.llm_provider import LLMProvider, LLMUsage
from tests.conftest import FIXTURE_VIDEO


class _FakeScoringProvider(LLMProvider):
    name = "fake"
    model = "fake-model"

    def generate(self, prompt: str) -> tuple[str, LLMUsage]:
        payload = {
            "hook_line": True,
            "self_contained": True,
            "emotional_peak": False,
            "quotable_line": "A quotable line.",
            "score": 75,
            "reason": "A solid, self-contained moment.",
        }
        return json.dumps(payload), LLMUsage(input_tokens=50, output_tokens=20, cost_usd=0.0001)


def _scored_pipeline(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> tuple[str, str, dict]:
    monkeypatch.setattr("app.services.jobs.get_llm_provider", lambda: _FakeScoringProvider())

    project_id = client.post("/projects", json={"name": "Review Project"}).json()["id"]
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
    client.post(f"/projects/{project_id}/sources/{source['id']}/score-candidates")

    candidates = client.get(f"/projects/{project_id}/sources/{source['id']}/candidates").json()
    assert len(candidates) > 0
    return project_id, source["id"], candidates[0]


def test_update_review_status_accept_then_reject(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id, source_id, candidate = _scored_pipeline(client, monkeypatch)
    assert candidate["review_status"] == "pending"

    accepted = client.patch(
        f"/projects/{project_id}/sources/{source_id}/candidates/{candidate['id']}",
        json={"review_status": "accepted"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["review_status"] == "accepted"

    rejected = client.patch(
        f"/projects/{project_id}/sources/{source_id}/candidates/{candidate['id']}",
        json={"review_status": "rejected"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["review_status"] == "rejected"


def test_update_candidate_times_persists_and_is_reflected_on_refetch(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id, source_id, candidate = _scored_pipeline(client, monkeypatch)

    transcript = client.get(f"/sources/{source_id}/transcript").json()
    segments = transcript["segments"]
    # Pick a valid, in-bounds (shorts_campaign: 15-60s) sentence-aligned span.
    new_start = segments[0]["start_ms"]
    new_end = next(s["end_ms"] for s in segments if s["end_ms"] - new_start >= 15_000)

    response = client.patch(
        f"/projects/{project_id}/sources/{source_id}/candidates/{candidate['id']}",
        json={"start_ms": new_start, "end_ms": new_end},
    )
    assert response.status_code == 200
    assert response.json()["start_ms"] == new_start
    assert response.json()["end_ms"] == new_end

    # The change is visible on a fresh fetch — "shows in the preview" reads
    # from this same persisted state, not from client-side-only state.
    refetched = client.get(f"/projects/{project_id}/sources/{source_id}/candidates").json()
    updated = next(c for c in refetched if c["id"] == candidate["id"])
    assert updated["start_ms"] == new_start
    assert updated["end_ms"] == new_end


def test_update_candidate_times_rejects_non_sentence_boundary(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id, source_id, candidate = _scored_pipeline(client, monkeypatch)

    response = client.patch(
        f"/projects/{project_id}/sources/{source_id}/candidates/{candidate['id']}",
        json={"start_ms": candidate["start_ms"] + 137, "end_ms": candidate["end_ms"]},
    )

    assert response.status_code == 400


def test_update_candidate_times_rejects_duration_outside_preset_bounds(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id, source_id, candidate = _scored_pipeline(client, monkeypatch)

    transcript = client.get(f"/sources/{source_id}/transcript").json()
    segments = transcript["segments"]
    # A single short sentence-to-sentence span, almost certainly under
    # shorts_campaign's 15s minimum.
    start = segments[0]["start_ms"]
    end = segments[0]["end_ms"]
    assume_too_short = end - start < 15_000
    assert assume_too_short  # sanity-check the fixture assumption

    response = client.patch(
        f"/projects/{project_id}/sources/{source_id}/candidates/{candidate['id']}",
        json={"start_ms": start, "end_ms": end},
    )

    assert response.status_code == 400


def test_update_candidate_returns_404_for_wrong_source(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id, source_id, candidate = _scored_pipeline(client, monkeypatch)
    other_source = client.post(
        f"/projects/{project_id}/sources",
        json={"title": "Other", "source_kind": "local_upload"},
    ).json()

    response = client.patch(
        f"/projects/{project_id}/sources/{other_source['id']}/candidates/{candidate['id']}",
        json={"review_status": "accepted"},
    )

    assert response.status_code == 404


def test_get_candidate_thumbnail_returns_jpeg(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id, source_id, candidate = _scored_pipeline(client, monkeypatch)

    response = client.get(
        f"/projects/{project_id}/sources/{source_id}/candidates/{candidate['id']}/thumbnail"
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert len(response.content) > 0
    assert response.content[:2] == b"\xff\xd8"  # JPEG magic bytes
