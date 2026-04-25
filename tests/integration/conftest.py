from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings
from src.db.postgres import Base


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine using the configured Postgres URL."""
    settings = get_settings()
    test_engine = create_engine(settings.postgres.database_url, echo=False)
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session(engine) -> Generator[Session, None, None]:
    """Provide a transactional session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    test_session = sessionmaker(bind=connection, expire_on_commit=False)()

    yield test_session

    test_session.close()
    transaction.rollback()
    connection.close()
