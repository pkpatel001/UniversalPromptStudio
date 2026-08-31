# Application development handoff

**Completed checkpoint:** A-002.2 — Prompt editing, deletion, organization, and local search
**Immediate checkpoint:** A-003 — Prompt composition and offline reference execution

## Current application baseline

A-002.2 completes the local prompt-library management lifecycle:

```text
desktop launch
    -> Rust resolves Tauri app_data_dir
        -> long-lived frozen Python sidecar
            -> schema-1 SQLite prompt library
                -> create/list/delete projects
                -> create/select/edit/delete project-owned prompts
                -> organize with category, tags, and ordered blocks
                -> deterministic project-scoped local search
```

The desktop automatically opens the local library. Users can create and select
projects, create and select prompts, edit title/category/tags, add/reorder/
enable/remove typed blocks, search titles/organization/block content, and
delete prompts or projects after explicit confirmation. All supported state
survives restart until explicitly deleted. Theme selection remains available.

SQLite remains only at the fixed `prompt-library.sqlite3` path under Tauri's
per-user app-data directory. Schema version 1 already contained every A-002.2
field, so no migration was added. The A-002.1 integrity, shape, relationship,
future-schema, unavailable-storage, and non-destructive recovery guarantees
remain unchanged.

The webview has ten fixed Tauri commands and no shell or filesystem authority.
Rust maps those calls to ten fixed sidecar commands and independently validates
correlation, identities, versions, capabilities, UUIDs, timestamps, ownership,
categories, tags, block types/order/content, confirmations, deletion results,
and bounded collections. Source-process and frozen installed-layout tests prove
edits, search, restart persistence, and deletion remain outside installation.

## A-003 — Prompt composition and offline reference execution

Turn the saved ordered blocks into the first usable composition and execution
flow. Deliver:

- deterministic composition of enabled blocks in stored order using the
  existing `PromptBuilder` and domain block types;
- a desktop composition preview that clearly distinguishes saved block content
  from the final assembled prompt;
- explicit offline execution through the already registered host-authored
  `ups.offline-echo` reference provider only;
- typed request/result IPC with bounded prompt text, provider identity,
  correlation, safe failures, and no arbitrary provider or option selection;
- presentation of the offline result and minimal non-secret execution metadata;
- deterministic service, IPC, frontend, Rust, frozen-sidecar, restart, and
  installed-path tests; and
- documentation of the transition from library management to controlled local
  composition/execution.

Do not add external endpoints, credentials, model discovery, streaming,
cancellation, retries, workflow authoring, background execution, history
persistence, arbitrary provider loading, arbitrary options, network access,
import/export, or sync. Controlled provider configuration begins in A-004.

## Subsequent application sequence

1. **A-004:** Controlled provider selection, endpoint configuration, and credential handling.
2. **A-005:** Workflow authoring, validation, and sequential execution UI.
3. **A-006:** Theme and managed extension lifecycle UI at supported trust boundaries.
4. **A-007:** Import/export, settings, diagnostics, onboarding, and distribution polish.

Each slice must produce a usable vertical outcome and reuse existing domain
contracts. Add Engineering capability only when the slice exposes a specific
gap.

## Starting points for A-003

- `Backend/application/prompt_builder.py`
- `Backend/application/services.py`
- `Backend/domain/models.py`
- `Backend/core/container.py`
- `Backend/ipc/router.py`
- `Backend/infrastructure/providers/runtime_adapter.py`
- `Frontend/src/backend-client.js`
- `Frontend/src/main.js`
- `Frontend/src-tauri/src/backend.rs`
- `Docs/04_Backend/IPC_PROTOCOL.md`

Before edits, verify clean local/origin/live GitHub parity and inspect the
A-002.2 acceptance evidence. Preserve the A-002.2 management lifecycle and the
schema-1 database. Keep the first execution path explicitly offline and
host-authored.
