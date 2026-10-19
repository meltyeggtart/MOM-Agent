from datetime import UTC, datetime

from fastapi.testclient import TestClient

VALID_MEETING = {
    "title": "Kickoff",
    "meeting_at": datetime(2026, 11, 2, 9, 30, tzinfo=UTC).isoformat(),
    "languages": ["en", "zh"],
    "client_company": "Acme",
    "project": "Apollo",
}


def test_create_returns_the_stored_meeting(client: TestClient) -> None:
    response = client.post("/meetings", json=VALID_MEETING)

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Kickoff"
    assert body["client_company"] == "Acme"
    assert body["project"] == "Apollo"
    assert body["languages"] == ["en", "zh"]
    assert body["status"] == "created"
    assert body["is_in_person"] is True
    assert body["id"]
    assert body["created_at"]
    assert body["updated_at"]


def test_read_returns_the_created_meeting(client: TestClient) -> None:
    created = client.post("/meetings", json=VALID_MEETING).json()

    response = client.get(f"/meetings/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["title"] == "Kickoff"
    assert body["meeting_at"] == created["meeting_at"]


def test_read_unknown_meeting_answers_not_found(client: TestClient) -> None:
    response = client.get("/meetings/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_create_rejects_an_empty_title(client: TestClient) -> None:
    response = client.post("/meetings", json={**VALID_MEETING, "title": ""})

    assert response.status_code == 422


def test_create_rejects_a_meeting_without_languages(client: TestClient) -> None:
    response = client.post("/meetings", json={**VALID_MEETING, "languages": []})

    assert response.status_code == 422


def test_create_rejects_an_unknown_language(client: TestClient) -> None:
    response = client.post("/meetings", json={**VALID_MEETING, "languages": ["fr"]})

    assert response.status_code == 422
