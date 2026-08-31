# Desktop-to-Python IPC protocol

**Checkpoint:** A-002.1
**Protocol:** 1
**Storage schema:** 1

## Topology

```text
Vite webview
    -> five fixed Tauri commands
        -> Rust BackendManager
            -> declared sidecar: universal-prompt-studio-backend
                -> ApplicationIpcRouter
                    -> one SQLite ApplicationContainer
                        -> prompt-library.sqlite3 in Tauri app data
```

Rust resolves Tauri's `app_data_dir`, creates that application-owned directory,
and passes it to the sidecar as `UPS_APP_DATA_DIR` after clearing the inherited
environment. Python appends only the fixed `prompt-library.sqlite3` filename.
The webview cannot provide an executable, path, environment value, Python
module, IPC command, or arbitrary payload.

The webview retains only `core:default`; it has no shell or filesystem
permission. The database is never placed in the repository, installation
directory, current working directory, or a webview-selected location.

## Transport

Rust lazily starts one long-lived target-triple sidecar. It writes one UTF-8
JSON object per line to stdin and reads one correlated JSON object per line from
stdout. Requests are serialized through one process lock. Rust terminates the
child when the manager is dropped or a transport failure invalidates it.

Messages are limited to 16,384 bytes. Requests and responses reject unknown or
duplicate fields, invalid UTF-8/JSON, non-finite numbers, unsupported protocol
versions, malformed identifiers, uncorrelated responses, and values outside
their command-specific bounds.

Request envelope:

```json
{
  "schema_version": 1,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "command": "library.projects.list",
  "payload": {}
}
```

Success envelope:

```json
{
  "schema_version": 1,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "ok": true,
  "result": {
    "projects": [],
    "has_more": false
  }
}
```

Failure envelope:

```json
{
  "schema_version": 1,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "ok": false,
  "error": {
    "code": "storage.unavailable",
    "message": "The prompt library database is unavailable."
  }
}
```

Rust allowlists error codes and replaces Python-authored messages with fixed
presentation messages. Unknown errors collapse to `backend.unavailable`.

## Fixed command surface

| Tauri command | Sidecar command | Exact payload | Result |
| --- | --- | --- | --- |
| `backend_readiness` | `application.readiness` | `{}` | Identity, application/protocol/storage versions, and exact capabilities |
| `library_projects` | `library.projects.list` | `{}` | Up to 50 project summaries plus `has_more` |
| `library_create_project` | `library.projects.create` | `name`, `description` | One created project summary |
| `library_prompts` | `library.prompts.list` | `project_id` | Up to 50 summaries owned by that project plus `has_more` |
| `library_create_prompt` | `library.prompts.create` | `project_id`, `title` | One created prompt summary |

Project names and prompt titles contain 1–120 trimmed characters. Project
descriptions contain at most 1,000 trimmed characters. Project and prompt IDs
are canonical lowercase UUID strings. Project and prompt summaries contain only
their fixed identifiers, bounded presentation text, and UTC timestamps.

Readiness result:

```json
{
  "status": "ready",
  "sidecar_identity": "com.universalpromptstudio.backend",
  "application_version": "0.2.0-alpha",
  "protocol_version": 1,
  "storage_schema_version": 1,
  "capabilities": [
    "application.readiness",
    "library.projects.list",
    "library.projects.create",
    "library.prompts.list",
    "library.prompts.create"
  ]
}
```

Rust verifies the exact sidecar identity, Cargo/application version, protocol
version, storage schema version, complete ordered capability list, response
schema, request correlation, entity fields, UUIDs, timestamps, collection
bounds, and project ownership before returning data to the frontend.

## SQLite lifecycle and recovery

The sidecar owns SQLite schema version 1 through `PRAGMA user_version`. A fresh,
empty database follows the explicit forward migration from version 0 to 1. All
connections enable foreign keys before use, use modern Python 3.12 transaction
control, disable trusted schema features, and apply a bounded busy timeout.

Startup performs an integrity check and validates the required tables and
columns. Recovery is fail-safe:

- a schema newer than 1 returns `storage.future_schema`;
- corrupt, incomplete, relationship-invalid, or unmanaged databases return
  `storage.invalid_database`;
- unavailable directories or database connections return
  `storage.unavailable`; and
- none of these paths delete, replace, rename, truncate, or automatically
  downgrade the user's database.

Project and prompt writes commit through repository-owned sessions. Prompt
foreign keys enforce project ownership. A restarted source process, frozen
sidecar, and installed-style sidecar all reopen the same app-data database and
show the saved records.

## Lifecycle and package boundary

- Development and release builds use the same frozen executable; there is no
  system-Python or checkout fallback.
- Responses must arrive within three seconds and match the request ID.
- Transport, timeout, malformed response, or process failure discards the
  child; a later action starts a fresh declared sidecar.
- Input or not-found failures do not discard a healthy process.
- `Scripts/build-sidecar.ps1` produces the target-triple executable and checksum
  manifest from the SHA-256-locked runtime set.
- The release system stages and independently checks the sidecar as the fifth
  release artifact alongside the unsigned NSIS installer.

## Trust boundary

The sidecar is trusted application code with the user's process authority; this
protocol is not a sandbox. Authority is reduced through exact schemas, five
fixed frontend commands, fixed sidecar commands and payloads, Tauri-owned app
data, bounded messages and values, fixed executable identity, minimal inherited
environment, correlation, timeout, checksum coverage, SQLite integrity/schema
checks, and crash recovery.

Primary guidance:

- <https://docs.rs/tauri/latest/tauri/path/struct.PathResolver.html>
- <https://v2.tauri.app/develop/sidecar/>
- <https://v2.tauri.app/security/capabilities/>
- <https://v2.tauri.app/plugin/shell/>
- <https://www.sqlite.org/pragma.html>
- <https://docs.sqlalchemy.org/en/20/dialects/sqlite.html>
