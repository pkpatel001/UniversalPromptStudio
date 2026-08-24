# Application development handoff

**Completed checkpoint:** A-001.1 — Explicit desktop-to-Python IPC foundation
**Immediate checkpoint:** A-001.2 — Bundled Python sidecar and installed lifecycle

## Current application baseline

A-001.1 establishes one real, non-destructive development path:

```text
frontend Check backend action
    -> Tauri backend_readiness command
        -> long-lived Rust-owned python -m Backend.ipc process
            -> application.readiness
                -> one in-memory ApplicationContainer
```

The boundary has schema-1 request/response envelopes, 16 KiB message limits,
strict fields and identifiers, one closed application command, request
correlation, a three-second timeout, structured safe failures, process reuse,
bounded shutdown, and frontend pending/ready/unavailable states.

The webview cannot choose a process, path, module, function, command, or payload.
No persistence, provider request, workflow run, network access, credential read,
or repository write occurs.

## A-001.2 — Bundled Python sidecar and installed lifecycle

Replace the debug-only system-Python launcher with an explicitly built and
declared Tauri sidecar/runtime. Deliver:

- a reproducible locked sidecar build from the application IPC entrypoint;
- target-triple-aware `externalBin` declaration and bundle integration;
- minimal Tauri permissions scoped only to that sidecar if the shell plugin is
  adopted;
- exact sidecar identity/version/protocol verification before readiness;
- installed start, reuse, timeout, crash/restart, and shutdown tests;
- package manifest/checksum coverage for the sidecar; and
- development and unsigned NSIS acceptance evidence.

Do not fall back to a system Python, compile-time checkout, arbitrary executable,
or broad shell permission in release builds. Do not add prompt persistence or
execution until the installed lifecycle is proven.

## Subsequent application sequence

1. **A-002:** Prompt-library SQLite persistence, organization, editing, and
   search.
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

## Starting points for A-001.2

- `Backend/ipc/`
- `Frontend/src/backend-client.js`
- `Frontend/src-tauri/src/backend.rs`
- `Frontend/src-tauri/tauri.conf.json`
- `Frontend/src-tauri/capabilities/default.json`
- `Engineering/ReleaseSystem/`
- `Scripts/package-desktop.ps1`
- `Docs/04_Backend/IPC_PROTOCOL.md`
- `Docs/ADR/ADR-0040-bounded-desktop-python-ipc-foundation.md`

Before edits, verify clean local/origin/live GitHub parity and recheck current
Tauri sidecar, capability, and shell-permission guidance from primary sources.
