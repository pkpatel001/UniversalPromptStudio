# Application development handoff

**Completed checkpoint:** A-007 — Import/export, settings, diagnostics,
onboarding, and distribution polish
**Immediate checkpoint:** None approved; select the next product outcome
explicitly before implementation

## Current application baseline

A-007 completes the approved A-001 through A-007 local desktop sequence:

```text
desktop launch
    -> Rust resolves Tauri app_data_dir
        -> long-lived frozen Python sidecar
            -> schema-1 prompt library and DPAPI provider credential boundary
            -> schema-1 workflow definitions
            -> managed theme state and session-only extension activation
            -> schema-1 non-secret application settings
        -> 37 exact desktop commands
            -> prompt/provider/workflow/customization surfaces
            -> first-run onboarding and device preferences
            -> selected prompt/workflow portable files
                -> validate and preview exact content
                -> explicit conflict action plus digest-bound confirmation
            -> redacted diagnostics and reviewed support export
```

Users can manage project-owned prompts, compose enabled durable blocks, execute
through offline echo or the fixed OpenAI Responses path, author and run bounded
sequential workflows, manage compatible themes, and explicitly activate
permissionless full-trust extensions for the current session.

The **Settings & support** dialog adds compact layout, reduced motion, selected
prompt/workflow export, reviewed import conflict handling, content-free
diagnostics, and reviewed support export. First-run onboarding explains local
storage and explicit execution. Telemetry is disabled and automatic updates are
unsupported.

## A-007 storage and portability boundary

`application-settings.json` is an atomic exact-shape schema-1 document below
per-user application data. It contains only onboarding completion, compact
layout, and reduced motion. Invalid settings fail unchanged. SQLite remains
schema 1.

Portable JSON contains exactly one prompt or one workflow and is limited to
10,000 Unicode characters. The webview uses its native file input and Blob
download; it has no Tauri filesystem or shell permission and sends no path.
Prompt imports target the currently open existing project. Every import is
validated and previewed before apply, reports exact conflict choices, and is
bound to the reviewed SHA-256 plus confirmation. Cross-project prompt identity
is never moved silently.

Diagnostics contain versions, package state, counts, provider availability and
credential state, customization counts, and non-secret preferences only.
Support export requires a redaction preview, acknowledgement, the reviewed
digest, and confirmation. Credentials, prompt content, workflow definitions and
runtime values, filesystem paths, environment values, extension code, and
contributions are excluded.

## Preserved trust boundary

- The webview exposes 37 fixed Tauri commands and no filesystem or shell
  authority.
- Messages remain capped at 16 KiB and protocol/storage versions remain 1.
- Provider credentials remain current-user DPAPI blobs and never enter portable
  files, settings, diagnostics, support data, SQLite, or web storage.
- Theme install remains fixed-inbox and exact-digest reviewed.
- Extension activation remains permissionless-manifest only, exact-digest,
  explicit full-trust, and session-only.
- Workflow operations remain the exact three host-owned contracts with explicit
  planning and execution confirmation.
- There is no bulk archive/restore, arbitrary destination, cloud sync,
  telemetry, automatic upload/update, remote marketplace, persistent extension
  approval, or signed publishing.
- The Windows x64 current-user NSIS package remains unsigned.

## Verification boundary

The checkpoint is accepted only when source tests, frontend tests/build, Rust
tests/format/strict Clippy, frozen-sidecar A-007 and earlier installed lifecycle
tests, the full Engineering build, complete Python suite, dependency audit, and
a fresh NSIS package all pass. Exact artifact sizes and SHA-256 values are
recorded in `A-007_ACCEPTANCE_EVIDENCE.md`.

Visual browser automation was attempted for the new dialogs. On this host the
browser runtime could not start because the Windows sandbox helper failed while
applying deny-read ACLs. This is an environment limitation; it does not replace
the deterministic frontend build, native dialog semantics, Rust validation, or
installed-process acceptance evidence.

## Next product decision

No A-008 scope is approved. Preserve the completed milestone boundary and choose
the next user outcome before changing implementation. Candidates such as bulk
backup/recovery, localization, advanced workflow behavior, automatic updating,
signing, publishing, or cloud features each require their own requirements and
trust/distribution decision.

Useful starting points for a future approved checkpoint:

- `Docs/09_Roadmap/A-007_ACCEPTANCE_EVIDENCE.md`
- `Docs/ADR/ADR-0046-controlled-product-portability-settings-and-redacted-support.md`
- `Docs/04_Backend/IPC_PROTOCOL.md`
- `Docs/05_Frontend/SETTINGS_PORTABILITY_AND_SUPPORT.md`
- `Docs/023_SECURITY.md`
- `Backend/application/product_hardening.py`
- `Frontend/src/product-ui.js`
- `Frontend/src-tauri/src/product.rs`
