# Application development handoff

**Completed checkpoint:** A-004 — Controlled provider selection, endpoint configuration, and credential handling
**Immediate checkpoint:** A-005 — Workflow authoring, validation, and bounded sequential execution UI

## Current application baseline

A-004 completes the first controlled configurable-provider runtime:

```text
desktop launch
    -> Rust resolves Tauri app_data_dir
        -> long-lived frozen Python sidecar
            -> schema-1 SQLite prompt library
                -> create/list/delete projects
                -> create/select/edit/delete project-owned prompts
                -> organize with category, tags, and ordered blocks
                -> deterministic project-scoped local search
                -> compose enabled saved blocks in durable order
                -> preview the final assembled prompt separately
                -> choose ups.offline-echo or ups.openai-responses
                -> persist bounded non-secret provider settings atomically
                -> protect the API key with current-user Windows DPAPI
                -> explicitly execute recomposed durable prompt state
```

The desktop automatically opens the local library. Users can create and select
projects, create and select prompts, edit title/category/tags, add/reorder/
enable/remove typed blocks, search titles/organization/block content, and
delete prompts or projects after explicit confirmation. All supported state
survives restart until explicitly deleted. Users can compose saved enabled blocks,
inspect the distinct final prompt, and explicitly run that durable state through
offline echo or the configured OpenAI Responses provider. Provider selection,
availability, bounded settings, credential save/clear, and execution are explicit.
Execution results remain ephemeral.

SQLite remains only at the fixed `prompt-library.sqlite3` path under Tauri's
per-user app-data directory and remains schema version 1. Non-secret provider
settings use atomic exact-shape `provider-settings.json`; the API key is stored
only as a DPAPI-protected blob below `credentials/`. The A-002.1 integrity,
shape, relationship,
future-schema, unavailable-storage, and non-destructive recovery guarantees
remain unchanged.

The webview has sixteen fixed Tauri commands and no shell or filesystem authority.
Rust maps those calls to sixteen fixed sidecar commands and independently validates
correlation, identities, versions, capabilities, UUIDs, timestamps, ownership,
categories, tags, block types/order/content, confirmations, deletion results,
bounded collections, composition counts/text, the two-provider catalog, endpoint,
credential reference/state, model and option bounds, execution correlation, and
output bounds. Source-process and frozen installed-layout tests prove management,
restart persistence, DPAPI redaction, composition, and offline execution.

## A-005 — Workflow authoring, validation, and bounded sequential execution UI

Expose the existing schema-1 Workflow SDK as the first product workflow slice.
Deliver:

- a bounded desktop authoring surface for workflow identity, nodes, edges, and
  node configuration using only schema-1 fields;
- deterministic validation and planning feedback before execution;
- operation choices populated only from the trusted host operation registry;
- explicit sequential execution with bounded intermediate and final values;
- a clear choice of existing authorized provider path where an operation needs
  prompt execution, without embedding credentials or arbitrary options;
- typed IPC and independent frontend/Rust/Python validation for workflow shapes,
  plans, execution events, results, confirmations, and safe failures; and
- deterministic service, frontend, Rust, restart, installed-layout, and boundary
  tests.

Do not add dynamic handlers, arbitrary operation IDs, plugin-supplied operations,
cycles, conditions, parallelism, retries, cancellation, background scheduling,
resume, history persistence, import/export, sync, or remote triggers.

## Subsequent application sequence

1. **A-005:** Workflow authoring, validation, and sequential execution UI.
2. **A-006:** Theme and managed extension lifecycle UI at supported trust boundaries.
3. **A-007:** Import/export, settings, diagnostics, onboarding, and distribution polish.

Each slice must produce a usable vertical outcome and reuse existing domain
contracts. Add Engineering capability only when the slice exposes a specific
gap.

## Starting points for A-005

- `Backend/application/services.py`
- `Backend/core/container.py`
- `Backend/ipc/router.py`
- `Backend/infrastructure/workflows.py`
- `Engineering/WorkflowSystem/`
- `Frontend/src/backend-client.js`
- `Frontend/src/main.js`
- `Frontend/src-tauri/src/backend.rs`
- `Docs/023_SECURITY.md`
- `Docs/04_Backend/IPC_PROTOCOL.md`

Before edits, verify clean local/origin/live GitHub parity and inspect the
A-004 acceptance evidence. Preserve the schema-1 prompt library, both current
provider paths, DPAPI credential boundary, exact settings schema, and ephemeral
execution policy. Reuse the Workflow SDK instead of creating a second graph model.
