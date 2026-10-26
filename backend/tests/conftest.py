import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.core.settings import settings
from app.db.session import get_session
from app.main import app
from app.services.consistency import ConsistencyReport, get_consistency_checker
from app.services.sensitive import SensitiveReport, get_sensitive_checker

PASSWORD = "correct-horse-42"


class _CleanSensitive:
    def check(self, document: object, secrets: object) -> SensitiveReport:
        return SensitiveReport()


class _CleanConsistency:
    def check(self, document: object) -> ConsistencyReport:
        return ConsistencyReport()


@pytest.fixture
def clean_checks() -> Iterator[None]:
    """Approval asks the model twice. Tests that do not care get clean verdicts."""
    app.dependency_overrides[get_sensitive_checker] = _CleanSensitive
    app.dependency_overrides[get_consistency_checker] = _CleanConsistency
    yield
    app.dependency_overrides.pop(get_sensitive_checker, None)
    app.dependency_overrides.pop(get_consistency_checker, None)


@pytest.fixture(scope="session")
def engine() -> Engine:
    return create_engine(settings.database_url, poolclass=NullPool)


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    """Wrap each test in a transaction that is rolled back afterwards.

    Commits made by the code under test only release a savepoint, so a test can never
    leave a row behind.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def sign_in(client: TestClient) -> str:
    """Register a fresh account and keep its session cookie on the client."""
    email = f"user-{uuid.uuid4().hex[:10]}@example.com"
    response = client.post(
        "/auth/register", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 201, response.text
    return email


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """A signed-in client, which is what most tests want."""
    app.dependency_overrides[get_session] = lambda: db_session
    try:
        with TestClient(app) as test_client:
            sign_in(test_client)
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def anonymous_client(db_session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_session] = lambda: db_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def other_client(db_session: Session) -> Iterator[TestClient]:
    """A second account, in its own cookie jar, sharing the same database."""
    app.dependency_overrides[get_session] = lambda: db_session
    try:
        with TestClient(app) as test_client:
            sign_in(test_client)
            yield test_client
    finally:
        app.dependency_overrides.clear()
