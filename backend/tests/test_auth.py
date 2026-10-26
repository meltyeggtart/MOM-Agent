import uuid
from datetime import UTC, datetime, timedelta

import pytest
from conftest import PASSWORD
from fastapi.testclient import TestClient
from sqlalchemy.orm import Query, Session

from app.db.models import User, UserSession

# These tests run against the development database, so a fixed address would collide
# with rows left behind by earlier runs. All three spellings normalise to ACCOUNT.
_SUFFIX = uuid.uuid4().hex[:8]
ACCOUNT = f"ana-{_SUFFIX}@example.com"
MIXED_CASE = f"Ana-{_SUFFIX}@Example.COM"
SHOUTING = f"ANA-{_SUFFIX}@EXAMPLE.COM"


def sessions_of(db_session: Session, email: str = ACCOUNT) -> Query[UserSession]:
    """Only this account's sessions, since the database is shared."""
    user = db_session.query(User).filter(User.email == email).one()
    return db_session.query(UserSession).filter(UserSession.user_id == user.id)


def register(client: TestClient, email: str, password: str = PASSWORD) -> dict:
    response = client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_register_signs_the_user_in(anonymous_client: TestClient) -> None:
    response = anonymous_client.post(
        "/auth/register",
        json={"email": MIXED_CASE, "password": PASSWORD},
    )

    assert response.status_code == 201
    assert response.json()["email"] == ACCOUNT
    cookie = response.headers["set-cookie"]
    assert "mom_session=" in cookie
    assert "HttpOnly" in cookie
    assert anonymous_client.get("/auth/me").status_code == 200


def test_register_rejects_a_duplicate_email(anonymous_client: TestClient) -> None:
    register(anonymous_client, ACCOUNT)

    response = anonymous_client.post(
        "/auth/register",
        json={"email": SHOUTING, "password": PASSWORD},
    )

    assert response.status_code == 409


def test_register_rejects_a_short_password(anonymous_client: TestClient) -> None:
    response = anonymous_client.post(
        "/auth/register", json={"email": ACCOUNT, "password": "short"}
    )

    assert response.status_code == 422


def test_register_rejects_an_invalid_email(anonymous_client: TestClient) -> None:
    response = anonymous_client.post(
        "/auth/register", json={"email": "not-an-email", "password": PASSWORD}
    )

    assert response.status_code == 400


def test_password_is_not_stored_in_plain_text(
    anonymous_client: TestClient, db_session: Session
) -> None:
    register(anonymous_client, ACCOUNT)

    stored = db_session.query(User).filter(User.email == ACCOUNT).one()

    assert stored.password_hash != PASSWORD
    assert stored.password_hash.startswith("scrypt$")


def test_login_accepts_the_right_password(anonymous_client: TestClient) -> None:
    register(anonymous_client, ACCOUNT)
    anonymous_client.post("/auth/logout")

    response = anonymous_client.post(
        "/auth/login", json={"email": ACCOUNT, "password": PASSWORD}
    )

    assert response.status_code == 200
    assert anonymous_client.get("/auth/me").json()["email"] == ACCOUNT


def test_login_rejects_a_wrong_password(anonymous_client: TestClient) -> None:
    register(anonymous_client, ACCOUNT)
    anonymous_client.post("/auth/logout")

    response = anonymous_client.post(
        "/auth/login", json={"email": ACCOUNT, "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"]


def test_login_does_not_reveal_unknown_emails(anonymous_client: TestClient) -> None:
    unknown = anonymous_client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )
    register(anonymous_client, ACCOUNT)
    anonymous_client.post("/auth/logout")
    wrong = anonymous_client.post(
        "/auth/login", json={"email": ACCOUNT, "password": "wrong-password"}
    )

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


def test_logout_ends_the_session(
    anonymous_client: TestClient, db_session: Session
) -> None:
    register(anonymous_client, ACCOUNT)

    response = anonymous_client.post("/auth/logout")

    assert response.status_code == 204
    assert anonymous_client.get("/auth/me").status_code == 401
    assert sessions_of(db_session).count() == 0


def test_an_expired_session_is_refused(
    anonymous_client: TestClient, db_session: Session
) -> None:
    register(anonymous_client, ACCOUNT)
    session = sessions_of(db_session).one()
    session.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    assert anonymous_client.get("/auth/me").status_code == 401


def test_the_session_token_is_not_stored_raw(
    anonymous_client: TestClient, db_session: Session
) -> None:
    register(anonymous_client, ACCOUNT)
    token = anonymous_client.cookies["mom_session"]

    stored = sessions_of(db_session).one()

    assert stored.token_hash != token
    assert len(stored.token_hash) == 64


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/meetings/00000000-0000-0000-0000-000000000000"),
        ("get", "/meetings/00000000-0000-0000-0000-000000000000/moms/internal"),
        ("post", "/meetings/00000000-0000-0000-0000-000000000000/moms/internal/approve"),
        ("get", "/meetings/00000000-0000-0000-0000-000000000000/moms/internal/export.pdf"),
        ("get", "/meetings/00000000-0000-0000-0000-000000000000/moms/internal/export.docx"),
        ("get", "/recordings/00000000-0000-0000-0000-000000000000/audio"),
    ],
)
def test_protected_routes_refuse_anonymous_callers(
    anonymous_client: TestClient, method: str, path: str
) -> None:
    response = getattr(anonymous_client, method)(path)

    assert response.status_code == 401


def test_creating_a_meeting_requires_an_account(
    anonymous_client: TestClient,
) -> None:
    response = anonymous_client.post(
        "/meetings",
        json={
            "title": "Kickoff",
            "meeting_at": "2026-11-02T09:30:00Z",
            "languages": ["en"],
        },
    )

    assert response.status_code == 401


def _document() -> dict:
    content = {
        "title": "Kickoff",
        "overview": "Budget held.",
        "topics": [],
        "decisions": [],
        "action_items": [],
        "open_questions": [],
        "internal_notes": [],
    }
    return {
        "source_language": "en",
        "audience": "internal",
        "visible_languages": ["en"],
        "versions": [
            {"language": language, "content": dict(content)}
            for language in ("en", "zh", "id")
        ],
    }


def test_a_meeting_cannot_be_read_by_another_account(
    client: TestClient, other_client: TestClient
) -> None:
    created = client.post(
        "/meetings",
        json={
            "title": "Kickoff",
            "meeting_at": "2026-11-02T09:30:00Z",
            "languages": ["en"],
        },
    ).json()

    assert client.get(f"/meetings/{created['id']}").status_code == 200
    assert other_client.get(f"/meetings/{created['id']}").status_code == 404


def test_another_account_cannot_touch_my_mom(
    client: TestClient, other_client: TestClient
) -> None:
    meeting_id = client.post(
        "/meetings",
        json={
            "title": "Kickoff",
            "meeting_at": "2026-11-02T09:30:00Z",
            "languages": ["en"],
        },
    ).json()["id"]
    document = _document()
    stored = client.post(
        f"/meetings/{meeting_id}/moms/internal/versions", json=document
    )
    assert stored.status_code == 201

    assert other_client.get(f"/meetings/{meeting_id}/moms/internal").status_code == 404
    assert (
        other_client.get(
            f"/meetings/{meeting_id}/moms/internal/export.pdf"
        ).status_code
        == 404
    )
    assert (
        other_client.put(
            f"/meetings/{meeting_id}/moms/internal/draft", json=document
        ).status_code
        == 404
    )
    assert (
        other_client.post(
            f"/meetings/{meeting_id}/moms/internal/approve"
        ).status_code
        == 404
    )
