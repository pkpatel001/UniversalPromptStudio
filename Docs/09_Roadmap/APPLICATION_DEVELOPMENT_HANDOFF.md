# Application development handoff

**Completed checkpoint:** A-005 — Workflow authoring, validation, and bounded sequential execution UI
**Immediate checkpoint:** A-006 — Theme and managed extension lifecycle UI at supported trust boundaries

## Current application baseline

A-005 completes the first product workflow slice:

```text
desktop launch
    -> Rust resolves Tauri app_data_dir
        -> long-lived frozen Python sidecar
            -> schema-1 SQLite prompt library
            -> atomic provider-settings.json and DPAPI credential blob
            -> atomic schema-1 workflow-definitions.json
                -> create/select/edit/delete bounded workflow definitions
                -> choose only three host-owned operations
                -> validate the current saved graph deterministically
                -> preview the ordered sequential plan or bounded failures
                -> confirm and execute one planned run
                -> present bounded step outputs and final values ephemerally
```

The prompt-library and provider outcomes from A-001 through A-004 remain
unchanged. Users can manage project-owned prompts, compose enabled saved blocks,
and explicitly execute through offline echo or the fixed OpenAI Responses path.
Provider settings remain bounded and non-secret; API keys remain protected by
current-user Windows DPAPI and never cross back to the webview.

The schema-1 workflow studio is part of the same scrollable workspace. It owns
workflow identity, typed boundary ports, trusted nodes, directed edges, planning
feedback, runtime inputs, confirmation, progress, intermediate results, and
final results. The trusted operation catalog is exactly `ups.echo-text`,
`ups.execute-saved-prompt`, and `ups.uppercase-text`. The saved-prompt operation
reuses current durable prompt/provider state and accepts no arbitrary prompt
text, endpoint, option, handler, or credential.

SQLite remains at the fixed `prompt-library.sqlite3` path under Tauri's per-user
app-data directory and remains schema version 1. Workflow definitions use the
separate exact-shape atomic `workflow-definitions.json` document. Plans, runs,
intermediate values, final values, and execution metadata are not persisted.
Invalid workflow storage fails without destructive recovery.

The webview has 24 fixed Tauri commands and no shell or filesystem authority.
Rust maps those calls to 24 fixed sidecar commands and independently validates
the A-001 through A-004 contracts plus workflow schemas, trusted operations and
ports, graph bounds, deterministic plans, typed runtime values, step/final
outcomes, confirmations, and run correlation. Source, frozen, restart, and
installed-layout tests prove workflow persistence, planning, and execution while
durable state remains below per-user app data.

## A-006 — Theme and managed extension lifecycle UI

Expose the existing Theme and Plugin SDK trust boundaries as the next bounded
product slice. Deliver:

- a desktop theme catalog and preview/apply/revert/remember flow using only the
  existing fixed semantic token contract;
- clear origin, compatibility, and trust-state presentation for themes and
  managed extensions;
- explicit bounded install/remove/enable/disable actions only where the
  Engineering lifecycle already defines a safe host-owned transition;
- no execution of unapproved package bytes or permission-requesting plugins;
- typed IPC and independent frontend/Rust/Python validation for catalogs,
  identities, compatibility, lifecycle plans, confirmations, and safe failures;
  and
- deterministic service, frontend, Rust, restart, installed-layout, and
  boundary tests.

Do not add a marketplace, remote discovery, automatic download/update,
publisher trust, signature infrastructure, arbitrary CSS/assets, arbitrary
plugin permissions, dynamic commands, webview filesystem authority, or silent
activation.

## Subsequent application sequence

1. **A-006:** Theme and managed extension lifecycle UI at supported trust boundaries.
2. **A-007:** Import/export, settings, diagnostics, onboarding, and distribution polish.

Each slice must produce a usable vertical outcome and reuse existing domain
contracts. Add Engineering capability only when the slice exposes a specific
gap.

## Starting points for A-006

- `Engineering/ThemeSystem/`
- `Engineering/PluginSystem/`
- `Frontend/src/theme-catalog.js`
- `Frontend/src/theme-controller.js`
- `Frontend/src/theme-preference.js`
- `Frontend/src/main.js`
- `Frontend/src-tauri/src/backend.rs`
- `Backend/core/container.py`
- `Backend/ipc/router.py`
- `Docs/023_SECURITY.md`
- `Docs/04_Backend/IPC_PROTOCOL.md`

Before edits, verify clean local/origin/live GitHub parity and inspect the A-005
acceptance evidence. Preserve the schema-1 prompt library, both provider paths,
DPAPI credential boundary, exact provider/workflow settings schemas, the trusted
three-operation workflow registry, deterministic planning, explicit execution,
and ephemeral run policy. Reuse ThemeSystem and PluginSystem rather than
creating second lifecycle models.
