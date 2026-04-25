import pytest
from pydantic import ValidationError

from src.config import PostgresSettings


class TestPostgresSettings:
    def test_valid_postgresql_url(self):
        settings = PostgresSettings(database_url="postgresql://user:pass@localhost:5432/db")
        assert settings.database_url == "postgresql://user:pass@localhost:5432/db"

    def test_valid_psycopg2_url(self):
        settings = PostgresSettings(
            database_url="postgresql+psycopg2://user:pass@localhost:5432/db"
        )
        assert settings.database_url.startswith("postgresql+psycopg2://")

    def test_invalid_url_scheme_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PostgresSettings(database_url="mysql://user:pass@localhost/db")

        assert "Database URL must start with" in str(exc_info.value)

    def test_default_pool_settings(self):
        settings = PostgresSettings()

        assert settings.pool_size == 20
        assert settings.max_overflow == 0
        assert settings.echo_sql is False
