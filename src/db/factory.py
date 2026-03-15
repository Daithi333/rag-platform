from src.config import get_settings
from src.db.interfaces.base import BaseDatabase
from src.db.interfaces.postgres import PostgresDatabase


def make_database() -> BaseDatabase:
    settings = get_settings()
    database = PostgresDatabase(settings=settings.postgres)
    database.startup()
    return database
