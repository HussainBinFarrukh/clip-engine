import json
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import FIXTURE_VIDEO


def _create_project(client: TestClient, name: str = "Demo Project") -> str:
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def test_upload_fixture_stores_original_and_metadata(
    client: TestClient, storage_root: Path
) -> None:
    project_id = _create_project(client)
    source = client.post(
        f"/projects/{project_id}/sources",
        json={"title": "Fixture Upload", "source_kind": "local_upload"},
    ).json()
    assert source["status"] == "draft"

    with FIXTURE_VIDEO.open("rb") as fixture_file:
        upload_response = client.post(
            f"/projects/{project_id}/sources/{source['id']}/upload",
            files={"file": ("speech_45s.mp4", fixture_file, "video/mp4")},
        )

    assert upload_response.status_code == 200
    updated = upload_response.json()
    assert updated["status"] == "uploaded"
    assert updated["duration_ms"] and updated["duration_ms"] > 0
    assert updated["width"] and updated["height"]

    assets_response = client.get(f"/projects/{project_id}/sources/{source['id']}/assets")
    assets = assets_response.json()
    assert len(assets) == 1
    assert assets[0]["asset_kind"] == "original_video"
    assert assets[0]["byte_size"] == FIXTURE_VIDEO.stat().st_size

    body_text = json.dumps(assets)
    assert "storage_key" not in body_text
    assert str(storage_root) not in body_text

    content_response = client.get(
        f"/projects/{project_id}/sources/{source['id']}/assets/{assets[0]['id']}/content"
    )
    assert content_response.status_code == 200
    assert len(content_response.content) == assets[0]["byte_size"]


def test_upload_rejects_unsupported_format(client: TestClient, tmp_path: Path) -> None:
    project_id = _create_project(client)
    source = client.post(
        f"/projects/{project_id}/sources",
        json={"title": "Bad Upload", "source_kind": "local_upload"},
    ).json()

    bad_file = tmp_path / "not-a-video.txt"
    bad_file.write_text("hello")

    with bad_file.open("rb") as f:
        response = client.post(
            f"/projects/{project_id}/sources/{source['id']}/upload",
            files={"file": ("not-a-video.txt", f, "text/plain")},
        )

    assert response.status_code == 415


def test_upload_rejects_when_source_kind_is_youtube_url(client: TestClient) -> None:
    project_id = _create_project(client)
    source = client.post(
        f"/projects/{project_id}/sources",
        json={
            "title": "YT",
            "source_kind": "youtube_url",
            "source_reference": "https://www.youtube.com/watch?v=abc12345678",
        },
    ).json()

    with FIXTURE_VIDEO.open("rb") as fixture_file:
        response = client.post(
            f"/projects/{project_id}/sources/{source['id']}/upload",
            files={"file": ("speech_45s.mp4", fixture_file, "video/mp4")},
        )

    assert response.status_code == 400


def test_create_source_rejects_non_youtube_reference(client: TestClient) -> None:
    project_id = _create_project(client)
    response = client.post(
        f"/projects/{project_id}/sources",
        json={
            "title": "Bad reference",
            "source_kind": "youtube_url",
            "source_reference": "https://example.com/video",
        },
    )
    assert response.status_code == 422


def test_create_source_rejects_missing_youtube_reference(client: TestClient) -> None:
    project_id = _create_project(client)
    response = client.post(
        f"/projects/{project_id}/sources",
        json={"title": "Missing URL", "source_kind": "youtube_url"},
    )
    assert response.status_code == 422


def test_create_source_for_missing_project_returns_404(client: TestClient) -> None:
    response = client.post(
        f"/projects/{uuid.uuid4()}/sources",
        json={"title": "Orphan", "source_kind": "local_upload"},
    )
    assert response.status_code == 404
