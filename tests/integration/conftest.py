from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings
from src.db.postgres import Base


@pytest.fixture(scope="session")
def engine():
    """Create a test engine pointing at the dedicated test database."""
    settings = get_settings()
    test_engine = create_engine(settings.postgres.test_database_url, echo=False)

    # Clean slate each test run
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session(engine) -> Generator[Session, None, None]:
    """Provide a transactional session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    test_session = sessionmaker(bind=connection, expire_on_commit=False)()

    # Repo methods call session.commit() — use a nested savepoint so
    # those commits hit the savepoint, not the outer transaction.
    test_session.begin_nested()

    yield test_session

    test_session.close()
    transaction.rollback()
    connection.close()
