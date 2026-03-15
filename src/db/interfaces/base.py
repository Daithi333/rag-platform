from abc import ABC, abstractmethod
from typing import ContextManager, TypeVar, Generic
from uuid import UUID

from sqlalchemy.orm import Session


ModelT = TypeVar("ModelT")
CreateSchemaT = TypeVar("CreateSchemaT")


class BaseDatabase(ABC):
    """Base class for database operations."""

    @abstractmethod
    def startup(self) -> None:
        """Initialize the database connection."""

    @abstractmethod
    def teardown(self) -> None:
        """Close the database connection."""

    @abstractmethod
    def get_session(self) -> ContextManager[Session]:
        """Get a database session."""


class BaseRepository(ABC, Generic[ModelT, CreateSchemaT]):
    def __init__(self, session: Session):
        self.session = session

    @abstractmethod
    def create(self, data: CreateSchemaT) -> ModelT: ...

    @abstractmethod
    def get_by_id(self, record_id: UUID) -> ModelT | None: ...

    @abstractmethod
    def update(self, record: ModelT) -> ModelT: ...

    @abstractmethod
    def delete(self, record_id: UUID) -> bool: ...

    @abstractmethod
    def list(self, limit: int = 100, offset: int = 0) -> list[ModelT]: ...
