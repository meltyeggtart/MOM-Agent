from fastapi.testclient import TestClient


def create_meeting(client: TestClient) -> str:
    response = client.post(
        "/meetings",
        json={
            "title": "Q3 kickoff",
            "meeting_at": "2026-10-20T09:00:00Z",
            "languages": ["en"],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def payload(audience: str = "internal", visible: list[str] | None = None) -> dict:
    return {
        "source_language": "en",
        "audience": audience,
        "visible_languages": visible or ["en", "zh", "id"],
        "versions": [
            {
                "language": language,
                "content": {
                    "title": f"Kickoff {language}",
                    "overview": "The team agreed to keep the budget.",
                },
            }
            for language in ("en", "zh", "id")
        ],
    }


def store(client: TestClient, meeting_id: str, body: dict | None = None) -> dict:
    response = client.post(
        f"/meetings/{meeting_id}/moms/internal/versions",
        json=body or payload(),
    )
    assert response.status_code == 201
    return response.json()


def test_stores_and_reads_a_draft(client: TestClient) -> None:
    meeting_id = create_meeting(client)

    stored = store(client, meeting_id)
    read = client.get(f"/meetings/{meeting_id}/moms/internal")

    assert stored["status"] == "draft"
    assert stored["versions"][0]["version_number"] == 1
    assert stored["versions"][0]["ai_generated"] is True
    assert read.status_code == 200
    assert read.json()["versions"][0]["content"]["versions"][0]["content"]["title"] == (
        "Kickoff en"
    )


def test_storing_twice_conflicts(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)

    again = client.post(
        f"/meetings/{meeting_id}/moms/internal/versions", json=payload()
    )

    assert again.status_code == 409


def test_edit_updates_the_draft(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    edited = payload()
    edited["versions"][0]["content"]["title"] = "Edited by the reviewer"

    response = client.put(f"/meetings/{meeting_id}/moms/internal/draft", json=edited)
    read = client.get(f"/meetings/{meeting_id}/moms/internal").json()

    assert response.status_code == 200
    assert read["versions"][0]["content"]["versions"][0]["content"]["title"] == (
        "Edited by the reviewer"
    )
    assert read["versions"][0]["ai_generated"] is False


def test_approval_locks_the_draft(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)

    approved = client.post(
        f"/meetings/{meeting_id}/moms/internal/approve",
        json={"approved_by": "Reviewer"},
    )
    blocked = client.put(
        f"/meetings/{meeting_id}/moms/internal/draft", json=payload()
    )

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["versions"][0]["approved_by"] == "Reviewer"
    assert approved.json()["versions"][0]["approved_at"] is not None
    assert blocked.status_code == 409


def test_approving_twice_conflicts(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    client.post(f"/meetings/{meeting_id}/moms/internal/approve")

    again = client.post(f"/meetings/{meeting_id}/moms/internal/approve")

    assert again.status_code == 409


def test_reopen_starts_a_new_version(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    client.post(f"/meetings/{meeting_id}/moms/internal/approve")

    reopened = client.post(f"/meetings/{meeting_id}/moms/internal/reopen").json()

    assert reopened["status"] == "draft"
    assert [v["version_number"] for v in reopened["versions"]] == [1, 2]
    assert reopened["versions"][0]["approved_at"] is not None
    assert reopened["versions"][1]["approved_at"] is None
    assert reopened["versions"][1]["ai_generated"] is False
    assert reopened["versions"][1]["content"] == reopened["versions"][0]["content"]


def test_reopen_before_approval_conflicts(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)

    response = client.post(f"/meetings/{meeting_id}/moms/internal/reopen")

    assert response.status_code == 409


def test_a_hidden_language_stays_stored(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id, payload(visible=["en", "id"]))

    read = client.get(f"/meetings/{meeting_id}/moms/internal").json()

    assert read["versions"][0]["content"]["visible_languages"] == ["en", "id"]
    assert len(read["versions"][0]["content"]["versions"]) == 3


def test_an_unknown_meeting_is_404(client: TestClient) -> None:
    missing = "00000000-0000-0000-0000-000000000000"

    assert client.get(f"/meetings/{missing}/moms/internal").status_code == 404
    assert (
        client.post(f"/meetings/{missing}/moms/internal/versions", json=payload()).status_code
        == 404
    )


def test_an_audience_mismatch_is_rejected(client: TestClient) -> None:
    meeting_id = create_meeting(client)

    response = client.post(
        f"/meetings/{meeting_id}/moms/internal/versions",
        json=payload(audience="external"),
    )

    assert response.status_code == 400


def test_languages_must_be_a_subset(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    body = payload()
    body["visible_languages"] = ["fr"]

    response = client.post(
        f"/meetings/{meeting_id}/moms/internal/versions", json=body
    )

    assert response.status_code == 422
