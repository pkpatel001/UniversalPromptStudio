# Application development handoff

**Completed checkpoint:** A-003 — Prompt composition and offline reference execution
**Immediate checkpoint:** A-004 — Controlled provider selection, endpoint configuration, and credential handling

## Current application baseline

A-003 completes the first controlled local prompt runtime:

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
                -> explicitly execute only through ups.offline-echo
```

The desktop automatically opens the local library. Users can create and select
projects, create and select prompts, edit title/category/tags, add/reorder/
enable/remove typed blocks, search titles/organization/block content, and
delete prompts or projects after explicit confirmation. All supported state
survives restart until explicitly deleted. Users can compose saved enabled blocks,
inspect the distinct final prompt, and explicitly run that durable state through
the offline echo provider. Execution results remain ephemeral.

SQLite remains only at the fixed `prompt-library.sqlite3` path under Tauri's
per-user app-data directory. Schema version 1 already contained every A-003
field, so no migration was added. The A-002.1 integrity, shape, relationship,
future-schema, unavailable-storage, and non-destructive recovery guarantees
remain unchanged.

The webview has twelve fixed Tauri commands and no shell or filesystem authority.
Rust maps those calls to twelve fixed sidecar commands and independently validates
correlation, identities, versions, capabilities, UUIDs, timestamps, ownership,
categories, tags, block types/order/content, confirmations, deletion results,
bounded collections, composition counts/text, fixed provider identity/version,
execution correlation, and output bounds. Source-process and frozen installed-layout
tests prove management, restart persistence, composition, and offline execution.

## A-004 — Controlled provider selection, endpoint configuration, and credential handling

Extend the fixed offline execution path into the first controlled configurable
provider path. Deliver:

- a desktop provider-settings surface populated only from host-authorized provider
  identities and metadata rather than arbitrary names or dynamic imports;
- bounded provider-specific endpoint, model, and option configuration through an
  explicit schema owned by the application;
- credential references backed by an OS-appropriate secret-storage abstraction,
  with secret values excluded from SQLite, web storage, logs, errors, and results;
- explicit provider selection per execution while preserving `ups.offline-echo`
  as the credential-free deterministic reference path;
- safe availability/validation feedback and one explicitly initiated configured
  provider execution path through the existing provider SDK boundary;
- typed IPC and independent frontend/Rust/Python validation for every new setting,
  identifier, credential reference, request, result, and safe failure; and
- deterministic service, security, frontend, Rust, restart, installed-path, and
  secret-redaction tests.

Do not add arbitrary provider loading, unrestricted endpoints/options, raw secret
transport to the webview, model discovery, streaming, cancellation, retries,
workflow authoring, background execution, history persistence, import/export,
sync, or marketplace behavior.

## Subsequent application sequence

1. **A-005:** Workflow authoring, validation, and sequential execution UI.
2. **A-006:** Theme and managed extension lifecycle UI at supported trust boundaries.
3. **A-007:** Import/export, settings, diagnostics, onboarding, and distribution polish.

Each slice must produce a usable vertical outcome and reuse existing domain
contracts. Add Engineering capability only when the slice exposes a specific
gap.

## Starting points for A-004

- `Backend/application/services.py`
- `Backend/domain/models.py`
- `Backend/core/container.py`
- `Backend/ipc/router.py`
- `Backend/infrastructure/providers/runtime_adapter.py`
- `Backend/interfaces/providers.py`
- `Engineering/ProviderSystem/`
- `Frontend/src/backend-client.js`
- `Frontend/src/main.js`
- `Frontend/src-tauri/src/backend.rs`
- `Docs/023_SECURITY.md`
- `Docs/04_Backend/IPC_PROTOCOL.md`

Before edits, verify clean local/origin/live GitHub parity and inspect the
A-003 acceptance evidence. Preserve the A-003 offline reference path and the
schema-1 library. Make credential storage and redaction decisions explicit before
adding any external provider execution.
