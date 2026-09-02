# Application development handoff

**Completed checkpoint:** A-006 — Theme and managed extension lifecycle UI at supported trust boundaries
**Immediate checkpoint:** A-007 — Import/export, settings, diagnostics, onboarding, and distribution polish

## Current application baseline

A-006 completes the managed customization slice:

```text
desktop launch
    -> Rust resolves Tauri app_data_dir
        -> long-lived frozen Python sidecar
            -> schema-1 prompt library and provider settings
            -> schema-1 workflow definitions
            -> fixed managed customization roots
                -> verified theme-package inbox
                -> active and reversibly disabled managed themes
                -> permissionless extension discovery
                    -> exact digest plus explicit trust confirmation
                    -> session-only activation
            -> strict catalog returned to the Customize surface
                -> inspect origin, compatibility, trust, digest, and restart state
                -> preview/apply/revert/remember compatible semantic themes
                -> confirm supported lifecycle changes
```

The prompt-library, provider, and workflow outcomes from A-001 through A-005
remain unchanged. Users can manage project-owned prompts, compose enabled saved
blocks, execute through offline echo or the fixed OpenAI Responses path, and
author/validate/execute bounded sequential workflows using only the three
host-owned operations.

The Customize dialog merges the three host-owned built-in themes with only
integrity-valid managed selections compiled from the existing semantic token
contract. External install requires a package already present in the fixed
app-data inbox, an exact package SHA-256, explicit external-package
acknowledgement, and confirmation. Disable and restore use the existing
reversible Engineering lifecycle and require the current approved digest. A
managed-theme integrity issue fails the dynamic catalog closed.

Extensions are discovered only below the fixed app-data extension root.
Permission-requesting plugins are blocked. Permissionless plugins require an
exact directory SHA-256, full-trust acknowledgement, and confirmation before
session activation. Approval and contributions are deliberately not persisted;
restart returns every extension to inactive. A-006 exposes no extension
install, removal, update, permission grant, or dynamic command.

SQLite remains at the fixed `prompt-library.sqlite3` path under Tauri's
per-user app-data directory and remains schema version 1. Provider settings,
DPAPI credential storage, and workflow definitions retain their separate
bounded documents. Theme receipts and disabled state persist only in the fixed
theme root. Runtime extension approval is ephemeral.

The webview has 29 fixed Tauri commands and no shell or filesystem authority.
Rust maps those calls to 29 fixed sidecar commands and independently validates
all earlier contracts plus customization catalogs, semantic tokens, canonical
identities, stable versions, exact digests, bounded issues, acknowledgements,
confirmations, and safe results. Frozen restart and installed-layout tests prove
theme persistence, reversible lifecycle, app-data containment, and
extension-approval reset.

## A-007 — Import/export, settings, diagnostics, onboarding, and distribution polish

Turn the completed local desktop slices into a coherent first-run and support
experience. Deliver:

- bounded import/export for explicitly selected supported data, with previews,
  conflict handling, and confirmation before durable changes;
- one settings surface for the existing non-secret provider, workflow,
  appearance, and application preferences without exposing credential values;
- presentation-safe diagnostics and support-bundle generation with explicit
  redaction and user review before any export;
- first-run onboarding that explains local storage, provider credentials,
  workflow execution, external-theme trust, and session-only extension trust;
- accessibility, empty/error/loading states, keyboard flow, and responsive
  layout polish across the completed desktop; and
- deterministic boundary, migration, restart, packaging, and installed-app
  acceptance tests plus distribution documentation.

Do not add cloud sync, background telemetry, automatic upload, marketplace or
remote discovery, automatic package/provider updates, arbitrary archive paths,
credential export, unreviewed diagnostic collection, silent conflict
resolution, persistent extension approval, or installer signing without an
explicit distribution decision.

## Subsequent application sequence

1. **A-007:** Import/export, settings, diagnostics, onboarding, and distribution polish.

Add Engineering capability only when this product slice exposes a specific gap.

## Starting points for A-007

- `Frontend/src/main.js`
- `Frontend/src/styles.css`
- `Frontend/src/customization-ui.js`
- `Frontend/src/backend-client.js`
- `Frontend/src-tauri/src/backend.rs`
- `Backend/core/container.py`
- `Backend/ipc/router.py`
- `Docs/023_SECURITY.md`
- `Docs/04_Backend/IPC_PROTOCOL.md`
- `Docs/09_Roadmap/A-006_ACCEPTANCE_EVIDENCE.md`

Before edits, verify clean local/origin/live GitHub parity and inspect the A-006
acceptance evidence. Preserve schema-1 prompt storage, the fixed provider and
DPAPI credential boundary, bounded workflow planning/execution, managed-theme
digest and receipt checks, fail-closed dynamic theme selection, permissionless
extension admission, and session-only extension activation.
