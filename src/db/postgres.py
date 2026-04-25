from contextlib import contextmanager
from typing import Generator

import structlog
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
from src.db.base import BaseDatabase
from src.config import PostgresSettings

logger = structlog.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class PostgresDatabase(BaseDatabase):
    """Postgres database implementation."""

    def __init__(self, settings: PostgresSettings):
        self.settings = settings
        self.engine: Engine | None = None
        self.session_factory: sessionmaker | None = None

    def startup(self) -> None:
        """Initialize the database connection."""
        try:
            url = self.settings.database_url
            logger.info(
                f"Attempting to connect to Postgres at: {url.split('@')[1] if '@' in url else 'localhost'}"
            )

            self.engine = create_engine(
                url,
                echo=self.settings.echo_sql,
                pool_size=self.settings.pool_size,
                max_overflow=self.settings.max_overflow,
                pool_pre_ping=True,  # Verify connections before use
            )

            self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

            # Test the connection
            assert self.engine is not None
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("Database connection test successful")

            # Check which tables exist before creating
            inspector = inspect(self.engine)
            existing_tables = set(inspector.get_table_names())

            # Create tables if they don't exist (idempotent operation)
            Base.metadata.create_all(bind=self.engine)

            # Check if any new tables were created
            updated_tables = inspector.get_table_names()
            new_tables = set(inspector.get_table_names()) - existing_tables

            if new_tables:
                logger.info(f"Created tables: {', '.join(new_tables)}")
            else:
                logger.info("All tables already exist - no new tables created")

            logger.info("Postgres database initialized successfully")
            assert self.engine is not None
            logger.info(f"Database: {self.engine.url.database}")
            logger.info(f"Total tables: {', '.join(updated_tables) if updated_tables else 'None'}")
            logger.info("Database connection established")

        except Exception as e:
            logger.error(f"Failed to initialize Postgres database: {e}")
            raise

    def teardown(self) -> None:
        """Close the database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Postgres database connections closed")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session."""
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call startup() first.")

        session = self.session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
