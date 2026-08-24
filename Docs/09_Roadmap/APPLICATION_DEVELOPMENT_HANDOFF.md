# Application development handoff

**Handoff boundary:** Engineering Toolkit complete through E-017.3
**Product phase:** Begin thin, user-visible vertical slices
**Immediate checkpoint:** A-001.1 — Explicit desktop-to-Python IPC foundation

## Objective

Stop adding toolkit capabilities speculatively. Connect the existing Tauri/Vite
shell to the existing Python application composition root through a narrow,
typed IPC boundary, then deliver usable prompt-management increments.

## Current product baseline

- `Frontend/src/main.js` renders the prompt-builder shell and controlled theme
  selection entirely in the webview.
- `Frontend/src-tauri/src/lib.rs` starts Tauri but exposes no application
  commands.
- `Backend/core/container.py` composes repositories, services, the offline echo
  provider, and the offline workflow reference runner.
- SQLite repositories, prompt/project services, search boundaries, provider
  execution, and workflow execution exist behind Python interfaces.
- No production bridge currently connects frontend actions to those services.

## A-001.1 — Explicit desktop-to-Python IPC foundation

Deliver one non-destructive end-to-end probe from the frontend through Tauri to
a long-lived Python application boundary and back. Define:

- a versioned request/response envelope with bounded JSON-compatible values;
- a closed command allowlist owned by the application layer;
- process lifecycle, startup timeout, shutdown, and unavailable-backend states;
- request correlation and structured safe errors;
- no shell interpolation, arbitrary module/function names, or data-selected
  commands;
- frontend pending/success/failure presentation; and
- unit, integration, and packaged-development verification.

The first probe should report application readiness or execute a harmless
offline echo. It should not introduce prompt persistence and IPC architecture in
the same checkpoint.

## Recommended application sequence

1. **A-001:** Desktop-to-Python IPC and lifecycle.
2. **A-002:** Prompt-library SQLite persistence, organization, editing, and
   search.
3. **A-003:** Prompt composition and offline reference execution.
4. **A-004:** Controlled provider selection, endpoint configuration, and
   credential handling.
5. **A-005:** Workflow authoring, validation, and sequential execution UI.
6. **A-006:** Theme and managed extension lifecycle UI at supported trust
   boundaries.
7. **A-007:** Import/export, settings, diagnostics, onboarding, and distribution
   polish.

Each slice must produce a usable vertical outcome and reuse existing domain
contracts. Add Engineering capability only when the slice exposes a specific
gap.

## Non-goals for A-001.1

- arbitrary Python execution or a generic RPC reflection layer;
- provider credentials or remote model access;
- database schema expansion;
- plugin loading in the UI process;
- workflow authoring;
- background auto-update or publishing; and
- reopening completed E-001 through E-017 milestones.

## Starting points

- `Frontend/src/main.js`
- `Frontend/src-tauri/src/lib.rs`
- `Backend/core/container.py`
- `Backend/application/services.py`
- `Backend/infrastructure/providers/runtime_adapter.py`
- `Backend/infrastructure/workflows.py`
- `Docs/01_Architecture/ENGINEERING_TOOLKIT.md`
- `Docs/09_Roadmap/ENGINEERING_TOOLKIT_CAPABILITY_MATRIX.md`

Before A-001.1 edits, verify a clean checkout and local/origin/live GitHub
parity, inspect Tauri v2 sidecar and IPC security constraints against current
primary documentation, and present a bounded implementation slice.
