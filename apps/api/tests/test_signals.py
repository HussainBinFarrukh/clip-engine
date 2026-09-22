from fastapi.testclient import TestClient

from tests.conftest import FIXTURE_VIDEO


def _upload_transcribe_and_wait(client: TestClient) -> tuple[str, str]:
    project_id = client.post("/projects", json={"name": "Signals Project"}).json()["id"]
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
    return project_id, source["id"]


def _signals_by_type(client: TestClient, project_id: str, source_id: str) -> dict:
    response = client.get(f"/projects/{project_id}/sources/{source_id}/signals")
    assert response.status_code == 200
    return {signal["signal_type"]: signal for signal in response.json()}


def test_extract_signals_stores_all_four_series(client: TestClient) -> None:
    project_id, source_id = _upload_transcribe_and_wait(client)

    response = client.post(f"/projects/{project_id}/sources/{source_id}/extract-signals")
    assert response.status_code == 200
    # Returns before the job runs, same contract as upload/transcribe.
    assert response.json()["status"] == "ready"

    signals = _signals_by_type(client, project_id, source_id)
    assert set(signals.keys()) == {"loudness_rms", "scene_change", "pause", "speech_rate"}

    loudness = signals["loudness_rms"]
    assert loudness["unit"] == "dbfs"
    assert len(loudness["points_json"]) > 0
    for point in loudness["points_json"]:
        assert -60.0 <= point["value"] <= 0.0
        assert point["t_ms"] >= 0

    speech_rate = signals["speech_rate"]
    assert speech_rate["unit"] == "wpm"
    assert len(speech_rate["points_json"]) == 8  # one per fixture sentence
    for point in speech_rate["points_json"]:
        assert point["value"] > 0

    pause = signals["pause"]
    assert pause["unit"] == "ms"
    for point in pause["points_json"]:
        assert point["duration_ms"] >= 300  # the pause threshold

    scene_change = signals["scene_change"]
    assert scene_change["unit"] == "event"
    # The fixture is a static color background: no real cuts expected.
    assert scene_change["points_json"] == []


def test_reextracting_signals_creates_no_duplicate_series(client: TestClient) -> None:
    project_id, source_id = _upload_transcribe_and_wait(client)

    first = client.post(f"/projects/{project_id}/sources/{source_id}/extract-signals")
    assert first.status_code == 200
    second = client.post(f"/projects/{project_id}/sources/{source_id}/extract-signals")
    assert second.status_code == 200

    response = client.get(f"/projects/{project_id}/sources/{source_id}/signals")
    signal_types = [signal["signal_type"] for signal in response.json()]
    assert sorted(signal_types) == sorted(set(signal_types))  # no repeats


def test_extract_signals_rejects_a_source_without_a_transcript(client: TestClient) -> None:
    project_id = client.post("/projects", json={"name": "No Transcript"}).json()["id"]
    source = client.post(
        f"/projects/{project_id}/sources",
        json={"title": "Draft", "source_kind": "local_upload"},
    ).json()

    response = client.post(f"/projects/{project_id}/sources/{source['id']}/extract-signals")

    assert response.status_code == 400


def test_list_signals_empty_before_extraction(client: TestClient) -> None:
    project_id, source_id = _upload_transcribe_and_wait(client)

    response = client.get(f"/projects/{project_id}/sources/{source_id}/signals")

    assert response.status_code == 200
    assert response.json() == []
