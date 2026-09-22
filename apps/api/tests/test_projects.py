import uuid

from fastapi.testclient import TestClient


def test_create_and_list_project(client: TestClient) -> None:
    response = client.post("/projects", json={"name": "Demo Project"})
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Demo Project"

    response = client.get("/projects")
    assert response.status_code == 200
    assert any(project["id"] == created["id"] for project in response.json())


def test_get_project_returns_404_when_missing(client: TestClient) -> None:
    response = client.get(f"/projects/{uuid.uuid4()}")
    assert response.status_code == 404


def test_create_project_rejects_empty_name(client: TestClient) -> None:
    response = client.post("/projects", json={"name": ""})
    assert response.status_code == 422
