# ADR-0042: Versioned app-data SQLite prompt library

**Status:** Accepted
**Date:** 2026-08-31
**Checkpoint:** A-002.1

## Context

A-001.2 proved a locked, installed Python sidecar but deliberately kept its
application container in memory and exposed readiness only. The first usable
offline slice needs durable project and prompt records without allowing the
webview to choose a database path or silently replacing user data when storage
is unavailable or incompatible.

Tauri provides an application-specific data directory derived from the bundle
identifier. SQLite reserves `PRAGMA user_version` for application-owned schema
versioning. SQLAlchemy's SQLite guidance requires deliberate transaction
control and explicit foreign-key activation on every connection.

## Decision

- Resolve `app_data_dir` in trusted Rust code, create that directory, and pass
  it to the sidecar through the fixed `UPS_APP_DATA_DIR` environment variable.
- Clear the sidecar environment first and retain no webview-selected path or
  filesystem capability.
- Append only the fixed `prompt-library.sqlite3` filename in Python.
- Own schema version 1 with `PRAGMA user_version` and an explicit forward
  migration from an empty version-0 database.
- Enable SQLite foreign keys on every connection, use Python 3.12 non-legacy
  transaction control, disable trusted schema features, and bound lock waits.
- Validate integrity, schema version, required tables/columns, and foreign-key
  relationships before exposing the library.
- Reject future, corrupt, unmanaged, incomplete, relationship-invalid, and
  unavailable databases with stable safe errors. Never delete, replace, rename,
  truncate, downgrade, or automatically repair those files.
- Add project ownership to persisted prompts and expose only five fixed IPC
  operations: readiness, project list/create, and project-scoped prompt
  list/create.
- Revalidate all Python results in Rust before returning camel-case values to
  the frontend. Limit returned collections to 50 records with `has_more`.
- Keep editing, deletion, organization, and local search in A-002.2.

## Consequences

The desktop now has a useful durable offline flow and reopens saved projects
and prompts after process or application restart. Development, frozen-sidecar,
and installed-style tests use the same database lifecycle and prove the
installation directory remains unchanged.

The application must preserve schema-1 databases through all later migrations.
Database recovery remains intentionally conservative: users receive a bounded
failure instead of an automatic destructive repair. Collection pagination
beyond the first 50 records and the remaining management operations belong to
later prompt-library checkpoints.

The sidecar remains trusted user-level code. This decision narrows authority
and validates data; it does not sandbox Python or SQLite.

## References

- <https://docs.rs/tauri/latest/tauri/path/struct.PathResolver.html>
- <https://www.sqlite.org/pragma.html>
- <https://docs.sqlalchemy.org/en/20/dialects/sqlite.html>
- `Docs/04_Backend/IPC_PROTOCOL.md`
- `Docs/ADR/ADR-0041-locked-python-sidecar-and-installed-lifecycle.md`
