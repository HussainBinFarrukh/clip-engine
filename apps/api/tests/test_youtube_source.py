import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.services.youtube import DownloadedVideo, YouTubeDownloadError
from tests.conftest import FIXTURE_VIDEO


class _FakeYouTubeProvider:
    def fetch(self, url: str, dest_dir: Path) -> DownloadedVideo:
        destination = dest_dir / "downloaded.mp4"
        shutil.copy(FIXTURE_VIDEO, destination)
        return DownloadedVideo(path=destination, title="Fake Downloaded Title")


class _FailingYouTubeProvider:
    def fetch(self, url: str, dest_dir: Path) -> DownloadedVideo:
        raise YouTubeDownloadError("simulated download failure")


def _create_project(client: TestClient) -> str:
    return client.post("/projects", json={"name": "YouTube Project"}).json()["id"]


def test_youtube_url_source_downloads_and_stores_asset(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.sources.get_youtube_provider", lambda: _FakeYouTubeProvider())

    project_id = _create_project(client)
    create_response = client.post(
        f"/projects/{project_id}/sources",
        json={
            "title": "My Clip",
            "source_kind": "youtube_url",
            "source_reference": "https://www.youtube.com/watch?v=abc12345678",
        },
    )
    assert create_response.status_code == 201
    # The endpoint returns before the download starts.
    assert create_response.json()["status"] == "downloading"

    source_id = create_response.json()["id"]

    # TestClient runs BackgroundTasks to completion before the request call returns,
    # so the download has already finished by this point.
    final = client.get(f"/projects/{project_id}/sources/{source_id}").json()
    assert final["status"] == "uploaded"
    assert final["duration_ms"] and final["duration_ms"] > 0

    assets = client.get(f"/projects/{project_id}/sources/{source_id}/assets").json()
    assert len(assets) == 1
    assert assets[0]["asset_kind"] == "original_video"


def test_youtube_url_download_failure_marks_source_failed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.sources.get_youtube_provider", lambda: _FailingYouTubeProvider())

    project_id = _create_project(client)
    create_response = client.post(
        f"/projects/{project_id}/sources",
        json={
            "title": "Broken Clip",
            "source_kind": "youtube_url",
            "source_reference": "https://youtu.be/abc12345678",
        },
    )
    source_id = create_response.json()["id"]

    final = client.get(f"/projects/{project_id}/sources/{source_id}").json()
    assert final["status"] == "failed"
    assert "simulated download failure" in final["error_message"]
