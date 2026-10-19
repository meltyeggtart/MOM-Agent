from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.core.settings import settings
from app.db.session import get_session
from app.main import app


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


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_session] = lambda: db_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
