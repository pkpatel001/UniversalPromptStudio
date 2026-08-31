"""Versioned SQLite repositories for the durable local prompt library."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    event,
    inspect,
    select,
)
from sqlalchemy.engine import URL, Connection, Engine
from sqlalchemy.exc import DatabaseError, SQLAlchemyError
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from Backend.domain.models import Project, Prompt, PromptBlock, PromptBlockType
from Backend.interfaces.providers import StorageProvider
from Backend.repositories.contracts import ProjectRepository, PromptRepository

CURRENT_SCHEMA_VERSION = 1
DATABASE_FILE_NAME = "prompt-library.sqlite3"


class SQLiteStorageError(RuntimeError):
    """Base class for safe storage lifecycle failures."""


class DatabaseUnavailableError(SQLiteStorageError):
    """The application-owned database cannot be opened or written."""


class InvalidDatabaseError(SQLiteStorageError):
    """The database is corrupt or does not match an owned schema."""


class FutureSchemaError(SQLiteStorageError):
    """The database was created by a newer application schema."""


class Base(DeclarativeBase):
    """Base class for SQLite ORM models."""


class ProjectRecord(Base):
    """SQLAlchemy record for projects."""

    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PromptRecord(Base):
    """SQLAlchemy record for prompts."""

    __tablename__ = "prompts"
    __table_args__ = (Index("ix_prompts_project_title", "project_id", "title"),)

    prompt_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.project_id"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    blocks: Mapped[list[PromptBlockRecord]] = relationship(
        back_populates="prompt",
        cascade="all, delete-orphan",
        order_by="PromptBlockRecord.order",
    )


class PromptBlockRecord(Base):
    """SQLAlchemy record for prompt blocks."""

    __tablename__ = "prompt_blocks"

    block_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt_id: Mapped[str] = mapped_column(ForeignKey("prompts.prompt_id"), nullable=False)
    block_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prompt: Mapped[PromptRecord] = relationship(back_populates="blocks")


_REQUIRED_COLUMNS = {
    "projects": {"project_id", "name", "description", "created_at"},
    "prompts": {
        "prompt_id",
        "project_id",
        "title",
        "category",
        "tags",
        "created_at",
        "updated_at",
    },
    "prompt_blocks": {
        "block_id",
        "prompt_id",
        "block_type",
        "content",
        "order",
        "enabled",
    },
}


class SQLiteStorageProvider(StorageProvider):
    """Own the SQLite connection, schema lifecycle, and session factory."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

    def initialize(self) -> None:
        """Validate or migrate the database without replacing user data."""

        existed = self.database_path.exists()
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            version, tables = self._inspect_database()
            if version > CURRENT_SCHEMA_VERSION:
                raise FutureSchemaError("The prompt library schema is newer than this app.")
            if version < 0:
                raise InvalidDatabaseError("The prompt library schema version is invalid.")
            if version == 0 and tables:
                raise InvalidDatabaseError("The prompt library has an unmanaged schema.")
            while version < CURRENT_SCHEMA_VERSION:
                version = self._apply_migration(version)
            self._validate_schema()
        except SQLiteStorageError:
            raise
        except DatabaseError as exc:
            if existed:
                raise InvalidDatabaseError("The prompt library database is invalid.") from exc
            raise DatabaseUnavailableError("The prompt library database is unavailable.") from exc
        except (OSError, SQLAlchemyError) as exc:
            raise DatabaseUnavailableError("The prompt library database is unavailable.") from exc

    @property
    def engine(self) -> Engine:
        """Return the SQLAlchemy engine, creating it lazily."""

        if self._engine is None:
            url = URL.create("sqlite", database=str(self.database_path))
            engine = create_engine(
                url,
                connect_args={"autocommit": False, "timeout": 5.0},
                future=True,
            )
            event.listen(engine, "connect", _configure_connection)
            self._engine = engine
        return self._engine

    def session(self) -> Session:
        """Create a new SQLAlchemy session."""

        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        return self._session_factory()

    def close(self) -> None:
        """Release pooled database connections."""

        if self._engine is not None:
            self._engine.dispose()

    def _inspect_database(self) -> tuple[int, set[str]]:
        with self.engine.connect() as connection:
            integrity = connection.exec_driver_sql("PRAGMA quick_check").scalar_one()
            if integrity != "ok":
                raise InvalidDatabaseError("The prompt library failed its integrity check.")
            version = int(connection.exec_driver_sql("PRAGMA user_version").scalar_one())
            tables = set(inspect(connection).get_table_names())
            return version, tables

    def _apply_migration(self, version: int) -> int:
        if version != 0:
            raise InvalidDatabaseError("The prompt library migration path is unavailable.")
        with self.engine.begin() as connection:
            _migrate_zero_to_one(connection)
        return 1

    def _validate_schema(self) -> None:
        with self.engine.connect() as connection:
            version = int(connection.exec_driver_sql("PRAGMA user_version").scalar_one())
            if version != CURRENT_SCHEMA_VERSION:
                raise InvalidDatabaseError("The prompt library schema version is invalid.")
            inspector = inspect(connection)
            tables = set(inspector.get_table_names())
            if not _REQUIRED_COLUMNS.keys() <= tables:
                raise InvalidDatabaseError("The prompt library schema is incomplete.")
            for table, required in _REQUIRED_COLUMNS.items():
                columns = {column["name"] for column in inspector.get_columns(table)}
                if not required <= columns:
                    raise InvalidDatabaseError("The prompt library schema is incompatible.")
            violations = connection.exec_driver_sql("PRAGMA foreign_key_check").first()
            if violations is not None:
                raise InvalidDatabaseError("The prompt library has invalid relationships.")


def _configure_connection(dbapi_connection: object, _record: object) -> None:
    connection = dbapi_connection
    previous_autocommit = connection.autocommit  # type: ignore[attr-defined]
    connection.autocommit = True  # type: ignore[attr-defined]
    cursor = connection.cursor()  # type: ignore[attr-defined]
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA trusted_schema=OFF")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()
        connection.autocommit = previous_autocommit  # type: ignore[attr-defined]


def _migrate_zero_to_one(connection: Connection) -> None:
    Base.metadata.create_all(connection)
    connection.exec_driver_sql("PRAGMA user_version = 1")


class SQLiteProjectRepository(ProjectRepository):
    """SQLite implementation of the project repository contract."""

    def __init__(self, storage_provider: SQLiteStorageProvider) -> None:
        self._storage_provider = storage_provider

    def add(self, project: Project) -> None:
        """Persist a project."""

        with self._storage_provider.session() as session:
            session.merge(
                ProjectRecord(
                    project_id=project.project_id,
                    name=project.name,
                    description=project.description,
                    created_at=project.created_at,
                )
            )
            session.commit()

    def get(self, project_id: str) -> Project | None:
        """Load a project by id."""

        with self._storage_provider.session() as session:
            record = session.get(ProjectRecord, project_id)
            return None if record is None else _project_from_record(record)

    def list(self) -> list[Project]:
        """Return projects ordered by name and stable identifier."""

        with self._storage_provider.session() as session:
            records = session.scalars(
                select(ProjectRecord).order_by(ProjectRecord.name, ProjectRecord.project_id)
            ).all()
            return [_project_from_record(record) for record in records]

    def delete(self, project_id: str) -> int | None:
        """Delete a project and all dependent prompts in one transaction."""

        with self._storage_provider.session() as session:
            project = session.get(ProjectRecord, project_id)
            if project is None:
                return None
            prompts = session.scalars(
                select(PromptRecord).where(PromptRecord.project_id == project_id)
            ).all()
            deleted_prompt_count = len(prompts)
            for prompt in prompts:
                session.delete(prompt)
            session.flush()
            session.delete(project)
            session.commit()
            return deleted_prompt_count


class SQLitePromptRepository(PromptRepository):
    """SQLite implementation of the prompt repository contract."""

    def __init__(self, storage_provider: SQLiteStorageProvider) -> None:
        self._storage_provider = storage_provider

    def add(self, prompt: Prompt) -> None:
        """Persist a prompt and its ordered blocks."""

        with self._storage_provider.session() as session:
            existing = session.get(PromptRecord, prompt.prompt_id)
            if existing is not None:
                session.delete(existing)
                session.flush()
            session.add(
                PromptRecord(
                    prompt_id=prompt.prompt_id,
                    project_id=prompt.project_id,
                    title=prompt.title,
                    category=prompt.category,
                    tags=_serialize_tags(prompt.tags),
                    created_at=prompt.created_at,
                    updated_at=prompt.updated_at,
                    blocks=[
                        PromptBlockRecord(
                            block_type=block.block_type.value,
                            content=block.content,
                            order=block.order,
                            enabled=block.enabled,
                        )
                        for block in sorted(prompt.blocks, key=lambda item: item.order)
                    ],
                )
            )
            session.commit()

    def get(self, prompt_id: str) -> Prompt | None:
        """Load a prompt by id."""

        with self._storage_provider.session() as session:
            record = session.get(PromptRecord, prompt_id)
            return None if record is None else _prompt_from_record(record)

    def list(self, project_id: str | None = None) -> list[Prompt]:
        """Return prompts ordered by title, optionally for one project."""

        statement = select(PromptRecord)
        if project_id is not None:
            statement = statement.where(PromptRecord.project_id == project_id)
        statement = statement.order_by(PromptRecord.title, PromptRecord.prompt_id)
        with self._storage_provider.session() as session:
            records = session.scalars(statement).all()
            return [_prompt_from_record(record) for record in records]

    def delete(self, prompt_id: str, project_id: str) -> bool:
        """Delete one prompt only when its ownership matches."""

        with self._storage_provider.session() as session:
            record = session.get(PromptRecord, prompt_id)
            if record is None or record.project_id != project_id:
                return False
            session.delete(record)
            session.commit()
            return True


def _project_from_record(record: ProjectRecord) -> Project:
    return Project(
        project_id=record.project_id,
        name=record.name,
        description=record.description,
        created_at=_as_utc(record.created_at),
    )


def _serialize_tags(tags: set[str]) -> str:
    """Serialize tags into a stable delimiter-separated string."""

    return "\n".join(sorted(tag.strip() for tag in tags if tag.strip()))


def _deserialize_tags(value: str) -> set[str]:
    """Deserialize persisted tags."""

    return {tag for tag in value.splitlines() if tag}


def _prompt_from_record(record: PromptRecord) -> Prompt:
    """Map a prompt ORM record to a domain prompt."""

    return Prompt(
        prompt_id=record.prompt_id,
        project_id=record.project_id,
        title=record.title,
        category=record.category,
        tags=_deserialize_tags(record.tags),
        created_at=_as_utc(record.created_at),
        updated_at=_as_utc(record.updated_at),
        blocks=[
            PromptBlock(
                block_type=PromptBlockType(block.block_type),
                content=block.content,
                order=block.order,
                enabled=block.enabled,
            )
            for block in record.blocks
        ],
    )


def _as_utc(value: datetime) -> datetime:
    """Return a timezone-aware UTC datetime after SQLite round-trip."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
