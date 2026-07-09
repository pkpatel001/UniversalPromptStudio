"""SQLite repository implementations backed by SQLAlchemy ORM."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from Backend.domain.models import Project, Prompt, PromptBlock, PromptBlockType
from Backend.interfaces.providers import StorageProvider
from Backend.repositories.contracts import ProjectRepository, PromptRepository


class Base(DeclarativeBase):
    """Base class for SQLite ORM models."""


class ProjectRecord(Base):
    """SQLAlchemy record for projects."""

    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PromptRecord(Base):
    """SQLAlchemy record for prompts."""

    __tablename__ = "prompts"

    prompt_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
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


class SQLiteStorageProvider(StorageProvider):
    """SQLite storage provider and SQLAlchemy session factory."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

    def initialize(self) -> None:
        """Create database tables and prepare the session factory."""

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(self.engine)

    @property
    def engine(self) -> Engine:
        """Return the SQLAlchemy engine, creating it lazily."""

        if self._engine is None:
            self._engine = create_engine(f"sqlite:///{self.database_path}", future=True)
        return self._engine

    def session(self) -> Session:
        """Create a new SQLAlchemy session."""

        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        return self._session_factory()


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
            if record is None:
                return None
            return Project(
                project_id=record.project_id,
                name=record.name,
                description=record.description,
                created_at=_as_utc(record.created_at),
            )


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

            record = PromptRecord(
                prompt_id=prompt.prompt_id,
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
            session.add(record)
            session.commit()

    def get(self, prompt_id: str) -> Prompt | None:
        """Load a prompt by id."""

        with self._storage_provider.session() as session:
            record = session.get(PromptRecord, prompt_id)
            if record is None:
                return None
            return _prompt_from_record(record)

    def list(self) -> list[Prompt]:
        """Return all prompts ordered by title."""

        with self._storage_provider.session() as session:
            records = session.scalars(select(PromptRecord).order_by(PromptRecord.title)).all()
            return [_prompt_from_record(record) for record in records]


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
