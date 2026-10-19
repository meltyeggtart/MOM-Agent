import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import recordings as recordings_api
from app.main import app
from app.services.storage import LocalAudioStorage, get_audio_storage

VALID_MEETING = {
    "title": "Kickoff",
    "meeting_at": datetime(2026, 11, 2, 9, 30, tzinfo=UTC).isoformat(),
    "languages": ["en", "zh"],
}

PAYLOAD = b"\x1aE\xdf\xa3fake-opus-bytes"


@pytest.fixture
def audio_root(tmp_path: Path) -> Iterator[Path]:
    root = tmp_path / "audio"
    app.dependency_overrides[get_audio_storage] = lambda: LocalAudioStorage(root=root)
    try:
        yield root
    finally:
        app.dependency_overrides.pop(get_audio_storage, None)


def _create_meeting(client: TestClient) -> str:
    return client.post("/meetings", json=VALID_MEETING).json()["id"]


def _upload(client: TestClient, meeting_id: str, **overrides: object):
    files = overrides.pop(
        "files", {"file": ("meeting.webm", PAYLOAD, "audio/webm;codecs=opus")}
    )
    return client.post(
        f"/meetings/{meeting_id}/recordings", files=files, data=overrides or None
    )


def _stored_files(root: Path) -> list[Path]:
    return sorted(root.iterdir()) if root.exists() else []


def test_upload_stores_the_audio_and_links_it_to_the_meeting(
    client: TestClient, audio_root: Path
) -> None:
    meeting_id = _create_meeting(client)

    response = _upload(client, meeting_id, duration_ms=4200)

    assert response.status_code == 201
    body = response.json()
    assert body["meeting_id"] == meeting_id
    assert body["content_type"] == "audio/webm"
    assert body["byte_size"] == len(PAYLOAD)
    assert body["duration_ms"] == 4200
    assert body["id"]
    assert body["uploaded_at"]

    stored = _stored_files(audio_root)
    assert len(stored) == 1
    assert stored[0].read_bytes() == PAYLOAD


def test_upload_sets_the_retention_expiry(client: TestClient, audio_root: Path) -> None:
    meeting_id = _create_meeting(client)

    body = _upload(client, meeting_id).json()

    uploaded_at = datetime.fromisoformat(body["uploaded_at"])
    expires_at = datetime.fromisoformat(body["expires_at"])
    assert timedelta(days=89) < expires_at - uploaded_at < timedelta(days=91)


def test_download_returns_the_stored_bytes(
    client: TestClient, audio_root: Path
) -> None:
    meeting_id = _create_meeting(client)
    recording = _upload(client, meeting_id).json()

    response = client.get(f"/recordings/{recording['id']}/audio")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/webm")
    assert response.content == PAYLOAD


def test_download_of_an_unknown_recording_answers_not_found(
    client: TestClient, audio_root: Path
) -> None:
    response = client.get(f"/recordings/{uuid.uuid4()}/audio")

    assert response.status_code == 404


def test_upload_for_an_unknown_meeting_answers_not_found(
    client: TestClient, audio_root: Path
) -> None:
    response = _upload(client, str(uuid.uuid4()))

    assert response.status_code == 404
    assert _stored_files(audio_root) == []


def test_upload_rejects_an_unsupported_content_type(
    client: TestClient, audio_root: Path
) -> None:
    meeting_id = _create_meeting(client)

    response = _upload(
        client,
        meeting_id,
        files={"file": ("notes.txt", b"not audio", "text/plain")},
    )

    assert response.status_code == 415
    assert _stored_files(audio_root) == []


def test_upload_rejects_an_empty_recording(
    client: TestClient, audio_root: Path
) -> None:
    meeting_id = _create_meeting(client)

    response = _upload(
        client, meeting_id, files={"file": ("meeting.webm", b"", "audio/webm")}
    )

    assert response.status_code == 400
    assert _stored_files(audio_root) == []


def test_upload_rejects_a_recording_over_the_limit(
    client: TestClient, audio_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    meeting_id = _create_meeting(client)
    monkeypatch.setattr(recordings_api, "MAX_UPLOAD_BYTES", 10)

    response = _upload(
        client, meeting_id, files={"file": ("meeting.webm", b"x" * 11, "audio/webm")}
    )

    assert response.status_code == 413
    assert _stored_files(audio_root) == []
