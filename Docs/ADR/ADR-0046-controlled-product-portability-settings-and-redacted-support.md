# ADR-0046: Controlled Product Portability, Settings, and Redacted Support

## Status

Accepted for A-007.

## Context

The completed desktop can persist prompts, provider settings, workflows, and
managed customization state. A first-run product also needs device preferences,
portable prompt/workflow files, and support diagnostics. Giving the webview a
filesystem capability, exporting the complete application-data directory, or
collecting unrestricted diagnostics would cross the existing trust boundary and
could expose credentials, user content, paths, runtime values, or extension
approval.

## Decision

A-007 adds eight fixed protocol commands while retaining the 16 KiB message
limit and storage schema 1.

Application preferences use one exact schema-1 `application-settings.json`
below the host-selected application-data directory. The complete document is
atomically replaced and contains only onboarding completion, compact layout,
and reduced motion. Language is fixed to English, telemetry is disabled, and
automatic updates remain unsupported. Invalid settings fail without repair or
replacement.

Portable files contain exactly one prompt or one workflow. They are canonical
JSON, limited to 10,000 Unicode characters, and returned to the webview as
content plus a safe filename—not a destination path. The browser-native file
picker and Blob download mechanism provide user-selected ingress and egress
without Tauri filesystem authority. Import always validates and previews the
exact document first. Durable apply requires the preview SHA-256, an allowed
explicit conflict action, and confirmation. Credentials, execution history,
extension approval, project names, and filesystem paths are excluded.

Diagnostics contain only application/package state, counts, provider
availability and credential state, managed-customization counts, and non-secret
preferences. Support export is a canonical redacted document. The UI must first
show included sections and the fixed redaction list; export then requires the
reviewed document SHA-256, redaction acknowledgement, and confirmation. Support
documents exclude credentials, prompt content, workflow definitions/runtime
values, paths, environment values, extension code, and contributions.

Python validates the durable/domain boundary, Rust independently validates
inputs and response shapes, and JavaScript validates the presentation contract.
No layer accepts a path, archive, arbitrary diagnostic field, silent conflict
choice, or unreviewed export.

## Consequences

- Users can move selected prompts and workflows between installations without
  copying application storage or credentials.
- First-run completion and accessibility preferences survive restart without a
  database migration.
- Support data is useful for version/count/state triage but deliberately cannot
  diagnose content-specific problems.
- There is no bulk backup/restore, archive import, cloud sync, telemetry,
  automatic upload, automatic updater, arbitrary destination, or credential
  portability.
- Windows release packages remain unsigned until a separate distribution
  signing decision is approved.
