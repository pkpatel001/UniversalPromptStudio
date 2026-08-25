# Application development handoff

**Completed checkpoint:** A-001.2 — Bundled Python sidecar and installed lifecycle
**Immediate checkpoint:** A-002.1 — SQLite prompt-library persistence foundation

## Current application baseline

A-001.2 establishes one installed-safe application path:

```text
frontend Check backend action
    -> Tauri backend_readiness command
        -> long-lived Rust-owned declared sidecar
            -> application.readiness
                -> one in-memory ApplicationContainer
```

The Python application is frozen by a SHA-256-locked PyInstaller toolchain,
named for the Rust target triple, declared through Tauri `externalBin`, and used
by both development and release builds. Rust verifies sidecar identity,
application version, protocol version, capability, schema, and correlation
before reporting ready.

The webview has no shell authority and cannot choose a process, path, argument,
module, function, IPC command, or payload. Lifecycle tests cover start, process
reuse, timeout behavior in the host, crash/restart, EOF shutdown, and execution
from an installed-style path. Release packaging records the sidecar as a
separate checksummed PE artifact in addition to the unsigned NSIS installer.

## A-002.1 — SQLite prompt-library persistence foundation

Replace the readiness-only in-memory product experience with the first durable,
offline prompt-library slice. Deliver:

- an application-owned SQLite database under the supported per-user app-data
  location, never the installation or repository directory;
- explicit schema creation and forward-only migration ownership;
- durable project and prompt creation plus project-scoped prompt listing;
- a minimal desktop library view that can create a project, create a prompt,
  restart the application, and show the saved records;
- typed IPC commands and frontend validation limited to that vertical flow;
- deterministic repository, service, IPC, frontend, restart, and installed-path
  tests; and
- recovery behavior for unavailable, invalid, or future-schema databases that
  does not silently destroy user data.

Do not add prompt execution, provider credentials, workflow authoring, import,
sync, arbitrary SQL, or broad filesystem access. Editing, deletion, full-text
search, and organization refinements belong to later A-002 checkpoints after
the persistence lifecycle is proven.

## Subsequent application sequence

1. **A-002.2:** Prompt editing, deletion, organization, and local search.
2. **A-003:** Prompt composition and offline reference execution.
3. **A-004:** Controlled provider selection, endpoint configuration, and
   credential handling.
4. **A-005:** Workflow authoring, validation, and sequential execution UI.
5. **A-006:** Theme and managed extension lifecycle UI at supported trust
   boundaries.
6. **A-007:** Import/export, settings, diagnostics, onboarding, and distribution
   polish.

Each slice must produce a usable vertical outcome and reuse existing domain
contracts. Add Engineering capability only when the slice exposes a specific
gap.

## Starting points for A-002.1

- `Backend/core/container.py`
- `Backend/infrastructure/repositories/sqlite.py`
- `Backend/application/services.py`
- `Backend/ipc/`
- `Frontend/src/backend-client.js`
- `Frontend/src/main.js`
- `Frontend/src-tauri/src/backend.rs`
- `Docs/04_Backend/IPC_PROTOCOL.md`

Before edits, verify clean local/origin/live GitHub parity and inspect current
Tauri app-data path, SQLite lifecycle, and migration guidance from primary
sources.
