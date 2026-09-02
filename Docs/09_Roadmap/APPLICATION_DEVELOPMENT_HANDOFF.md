# Application development handoff

**Completed checkpoint:** A-008 — Beginner-friendly user guide and in-app help
**Immediate checkpoint:** None approved; select the next product outcome
explicitly before implementation

## Current application baseline

A-008 completes the approved A-001 through A-008 local desktop sequence:

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
            -> fixed frontend Help catalog
                -> 15 offline task topics and deterministic local search
                -> contextual entry points from major product surfaces
                -> safe text-node rendering and related-topic navigation

The workspace remains an offline-first project and prompt library with saved
ordered blocks, deterministic composition, explicit provider execution, bounded
sequential workflows, managed themes, and exact-digest full-trust extensions for
the current session.

Settings & support retains compact layout, reduced motion, selected
prompt/workflow export, reviewed import conflict handling, content-free
diagnostics, and reviewed support export. First-run onboarding explains local
storage and explicit execution. Telemetry is disabled and automatic updates are
unsupported.

## A-008 help and learning boundary

Help content is an application-owned, fixed catalog of 15 topics. It covers
installation, first use, projects, prompt authoring, block types, composition,
offline and OpenAI provider execution, workflows, portability, settings,
diagnostics, managed customization, stress testing, troubleshooting, privacy,
distribution, and terminology.

Search normalizes case and accents and requires every entered term to match the
authored topic text. It does not inspect prompt content, application data,
diagnostics, provider responses, files, or network sources. Article content and
navigation labels are created with text nodes; the catalog cannot inject
arbitrary HTML.

The native modal Help dialog uses normal tab order, Escape behavior, a live
result count, responsive layout, and semantic theme tokens. The workspace opens
the beginner quick start. Prompt blocks, prompt composition/provider execution,
workflows, themes/extensions, portability, and settings/support open the
matching topic directly.

The long-form Docs/05_Frontend/USER_GUIDE.md is the complete beginner manual. It
documents the unsigned Windows alpha, first-run path, prompt recipes, OpenAI
credential boundary, workflows, single-item portability, trusted extensions,
redacted support, a repeatable stress-test plan, troubleshooting, privacy,
limitations, and a glossary.

A-008 adds no Rust or Python implementation, no IPC command, no protocol or
schema version, no Tauri permission, no filesystem picker, no web storage, no
network request, no background task, and no extension authority. The desktop
boundary remains protocol 1, SQLite schema 1, workflow schema 1, settings schema
1, and 37 exact commands.

## Preserved A-007 boundaries

Application settings remain an atomic exact-shape schema-1 document containing
only onboarding completion, compact layout, and reduced motion. Portable JSON
contains exactly one prompt or workflow and is limited to 10,000 Unicode
characters. Prompt imports target the currently open existing project and every
import is previewed before a digest-bound confirmed apply.

Diagnostics continue to contain versions, package state, counts, provider
availability and credential state, customization counts, and non-secret
preferences only. Credentials, prompt/workflow content, paths, environment
values, and extension code remain excluded. Support download remains bound to
the reviewed SHA-256 and confirmation.

## Important limits

- The application and help catalog are currently English-only.
- In-app Help is static and offline; it has no screenshots, remote updates,
  interactive automation, or access to user content.
- There is no bulk archive/restore, arbitrary destination, cloud sync,
  telemetry, automatic upload/update, remote marketplace, persistent extension
  approval, or signed publishing.
- OpenAI API use is external and can incur charges; current pricing and model
  availability are provider concerns.
- The Windows x64 current-user NSIS package remains unsigned.
- The user guide documents the supported alpha; it does not claim suitability
  for regulated production workloads.

## Verification boundary

The checkpoint is accepted only when catalog unit tests, all frontend tests and
the production build, dependency audit, complete Python suite, Rust
tests/format/strict Clippy, the full Engineering build, and a fresh Windows NSIS
package pass. Artifact sizes, SHA-256 values, Authenticode state, and invariant
checks are recorded in A-008_ACCEPTANCE_EVIDENCE.md.

## Next product decision

No A-009 scope is approved. Preserve the completed milestone boundary and choose
the next user outcome before changing implementation. Bulk backup/recovery,
localization, automatic updates, signing/publishing, advanced workflow behavior,
or cloud features each require separate requirements and trust/distribution
decisions.

Useful starting points for a future approved checkpoint:

- Docs/09_Roadmap/A-008_ACCEPTANCE_EVIDENCE.md
- Docs/05_Frontend/USER_GUIDE.md
- Docs/05_Frontend/UI_ARCHITECTURE.md
- Docs/034_KNOWN_LIMITATIONS.md
- Frontend/src/help-catalog.js
- Frontend/src/help-ui.js
- Frontend/src/help.css
- Docs/023_SECURITY.md
