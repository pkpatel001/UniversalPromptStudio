# Application development handoff

**Completed checkpoint:** A-002.1 — SQLite prompt-library persistence foundation
**Immediate checkpoint:** A-002.2 — Prompt editing, deletion, organization, and local search

## Current application baseline

A-002.1 establishes the first durable offline product flow:

```text
desktop launch
    -> Rust resolves Tauri app_data_dir
        -> long-lived frozen Python sidecar
            -> schema-1 SQLite prompt library
                -> create/list projects
                -> create/list project-owned prompts
```

The minimal desktop library automatically starts the backend, creates a project,
creates prompts inside the selected project, and shows the same saved records
after application restart. Theme selection remains available.

SQLite lives only at the fixed `prompt-library.sqlite3` path under Tauri's
per-user app-data directory. Schema version 1 has explicit forward migration
ownership, foreign-key enforcement, integrity and shape checks, and safe
failures for unavailable, corrupt, unmanaged, incomplete, relationship-invalid,
or future-schema databases. Recovery never silently destroys user data.

The webview has five fixed Tauri commands and no shell or filesystem authority.
Rust maps those calls to five fixed sidecar commands, validates all entity and
collection results, and allowlists safe errors. Source-process, frozen-sidecar,
restart, crash, and installed-layout tests prove persistence stays outside the
installation directory.

## A-002.2 — Prompt editing, deletion, organization, and local search

Extend the proven persistence lifecycle into a usable management flow. Deliver:

- prompt title and ordered-block editing with explicit validation and durable
  update timestamps;
- explicit prompt deletion and project deletion with clear confirmation and
  defined dependent-prompt behavior;
- category and tag organization through the existing domain fields;
- deterministic local prompt search scoped to supported project/library
  boundaries;
- desktop views for selecting, editing, organizing, searching, and deleting
  saved prompts without exposing arbitrary SQL or filesystem paths;
- forward-only schema migration only where A-002.2 persistence changes require
  it, preserving schema-1 user data;
- typed IPC and frontend validation for the exact new operations; and
- deterministic repository, service, IPC, frontend, migration, restart, and
  installed-path tests.

Do not add provider execution, credentials, remote endpoints, workflow
authoring, sync, import/export, arbitrary SQL, arbitrary filesystem access, or
background indexing outside the application-owned data directory. Prompt
composition and offline reference execution begin in A-003 after the local
library management lifecycle is complete.

## Subsequent application sequence

1. **A-003:** Prompt composition and offline reference execution.
2. **A-004:** Controlled provider selection, endpoint configuration, and credential handling.
3. **A-005:** Workflow authoring, validation, and sequential execution UI.
4. **A-006:** Theme and managed extension lifecycle UI at supported trust boundaries.
5. **A-007:** Import/export, settings, diagnostics, onboarding, and distribution polish.

Each slice must produce a usable vertical outcome and reuse existing domain
contracts. Add Engineering capability only when the slice exposes a specific
gap.

## Starting points for A-002.2

- `Backend/domain/models.py`
- `Backend/repositories/contracts.py`
- `Backend/infrastructure/repositories/sqlite.py`
- `Backend/application/services.py`
- `Backend/ipc/router.py`
- `Frontend/src/backend-client.js`
- `Frontend/src/main.js`
- `Frontend/src-tauri/src/backend.rs`
- `Docs/04_Backend/IPC_PROTOCOL.md`

Before edits, verify clean local/origin/live GitHub parity and inspect the
current schema-1 acceptance evidence. Preserve schema-1 databases through any
new migration and keep project/prompt ownership explicit.
