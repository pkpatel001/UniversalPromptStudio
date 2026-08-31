"""A-002.1 durable prompt-library schema and recovery tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from Backend.core.container import (
    DESKTOP_APP_DATA_ENV,
    create_desktop_container,
    create_sqlite_container,
)
from Backend.domain.models import Prompt
from Backend.infrastructure.repositories.sqlite import (
    CURRENT_SCHEMA_VERSION,
    DATABASE_FILE_NAME,
    DatabaseUnavailableError,
    FutureSchemaError,
    InvalidDatabaseError,
    SQLitePromptRepository,
    SQLiteStorageProvider,
)


def _pragma(path: Path, name: str) -> int:
    with sqlite3.connect(path) as connection:
        return int(connection.execute(f"PRAGMA {name}").fetchone()[0])


def test_new_database_runs_owned_forward_migration(tmp_path: Path) -> None:
    database = tmp_path / "app-data" / DATABASE_FILE_NAME
    storage = SQLiteStorageProvider(database)

    storage.initialize()

    assert database.is_file()
    assert _pragma(database, "user_version") == CURRENT_SCHEMA_VERSION
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
        }
        columns = {row[1] for row in connection.execute("PRAGMA table_info(prompts)")}
    assert {"projects", "prompts", "prompt_blocks"} <= tables
    assert "project_id" in columns
    storage.close()


def test_project_prompt_records_survive_container_restart(tmp_path: Path) -> None:
    database = tmp_path / DATABASE_FILE_NAME
    first = create_sqlite_container(database)
    project = first.project_service.create_project(" Product ", " Offline prompts ")
    first.prompt_service.create_library_prompt(project.project_id, " First prompt ")
    first.prompt_service.create_library_prompt(project.project_id, " Second prompt ")

    second = create_sqlite_container(database)

    assert second.project_service.list_projects() == [project]
    assert [
        prompt.title for prompt in second.prompt_service.list_project_prompts(project.project_id)
    ] == [
        "First prompt",
        "Second prompt",
    ]


def test_prompt_lists_are_strictly_project_scoped(tmp_path: Path) -> None:
    container = create_sqlite_container(tmp_path / DATABASE_FILE_NAME)
    first = container.project_service.create_project("First")
    second = container.project_service.create_project("Second")
    container.prompt_service.create_library_prompt(first.project_id, "Only first")
    container.prompt_service.create_library_prompt(second.project_id, "Only second")

    assert [
        prompt.title for prompt in container.prompt_service.list_project_prompts(first.project_id)
    ] == ["Only first"]
    assert [
        prompt.title for prompt in container.prompt_service.list_project_prompts(second.project_id)
    ] == ["Only second"]


def test_foreign_keys_reject_unknown_project_ownership(tmp_path: Path) -> None:
    storage = SQLiteStorageProvider(tmp_path / DATABASE_FILE_NAME)
    storage.initialize()
    repository = SQLitePromptRepository(storage)

    with pytest.raises(IntegrityError):
        repository.add(
            Prompt(
                title="Orphan",
                project_id="550e8400-e29b-41d4-a716-446655440000",
            )
        )


def test_future_schema_is_rejected_without_mutation(tmp_path: Path) -> None:
    database = tmp_path / DATABASE_FILE_NAME
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE future_data (value TEXT NOT NULL)")
        connection.execute("INSERT INTO future_data VALUES ('preserve me')")
        connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION + 1}")
    before = database.read_bytes()

    with pytest.raises(FutureSchemaError):
        SQLiteStorageProvider(database).initialize()

    assert database.read_bytes() == before


def test_invalid_and_unmanaged_databases_are_left_unchanged(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.sqlite3"
    invalid.write_bytes(b"not a sqlite database")
    invalid_before = invalid.read_bytes()
    with pytest.raises(InvalidDatabaseError):
        SQLiteStorageProvider(invalid).initialize()
    assert invalid.read_bytes() == invalid_before

    unmanaged = tmp_path / "unmanaged.sqlite3"
    with sqlite3.connect(unmanaged) as connection:
        connection.execute("CREATE TABLE user_content (value TEXT NOT NULL)")
        connection.execute("INSERT INTO user_content VALUES ('preserve me')")
    unmanaged_before = unmanaged.read_bytes()
    with pytest.raises(InvalidDatabaseError):
        SQLiteStorageProvider(unmanaged).initialize()
    assert unmanaged.read_bytes() == unmanaged_before


def test_unavailable_database_path_does_not_replace_blocking_file(tmp_path: Path) -> None:
    blocking = tmp_path / "not-a-directory"
    blocking.write_text("preserve me", encoding="utf-8")

    with pytest.raises(DatabaseUnavailableError):
        SQLiteStorageProvider(blocking / DATABASE_FILE_NAME).initialize()

    assert blocking.read_text(encoding="utf-8") == "preserve me"


def test_desktop_container_uses_only_configured_app_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_data = tmp_path / "per-user-app-data"
    monkeypatch.setenv(DESKTOP_APP_DATA_ENV, str(app_data))

    container = create_desktop_container()
    project = container.project_service.create_project("Installed")

    assert (app_data / DATABASE_FILE_NAME).is_file()
    assert container.project_repository.get(project.project_id) == project


def test_desktop_container_rejects_missing_or_relative_app_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(DESKTOP_APP_DATA_ENV, raising=False)
    with pytest.raises(DatabaseUnavailableError):
        create_desktop_container()
    monkeypatch.setenv(DESKTOP_APP_DATA_ENV, "relative/path")
    with pytest.raises(DatabaseUnavailableError):
        create_desktop_container()
