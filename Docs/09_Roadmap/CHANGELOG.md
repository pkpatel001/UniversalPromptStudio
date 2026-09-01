# Changelog

## Unreleased — 0.2.0-alpha

### Engineering Toolkit closure

- Completed E-001 through E-017 engineering milestones.
- Added deterministic build, local release packaging, and shared manifest
  validation.
- Added controlled plugin, AI-provider, theme, and workflow SDK/runtime
  boundaries.
- Added allowlisted Engineering self-generation with rollback, artifact
  manifests, and no-write drift verification.
- Consolidated toolkit architecture, capability boundaries, readiness guidance,
  and the application-development handoff.

### Product status

- Added a strict schema-1 JSON-lines readiness protocol owned by the Python
  application layer.
- Added a hash-locked, target-triple Python sidecar declared through Tauri, with
  exact identity/version/protocol verification and Rust-owned lifecycle.
- Added real frozen-process start, reuse, crash/restart, shutdown, installed-path,
  unsigned NSIS, and sidecar checksum coverage.
- Added frontend pending, ready, and unavailable presentation.
- Added schema-1 SQLite persistence under Tauri-managed app data with explicit
  migration ownership and non-destructive corrupt/future-schema recovery.
- Added durable project creation/listing and project-owned prompt
  creation/listing across source, frozen-sidecar, restart, and installed paths.
- Added durable prompt title, category, tag, and ordered-block editing while
  retaining schema version 1 and existing user data.
- Added deterministic case-insensitive local search scoped to the selected
  project across titles, categories, tags, and block content.
- Added explicit prompt deletion and project deletion with dependent-prompt
  removal, confirmation, ownership validation, and installed restart coverage.
- Replaced the readiness-only screen with the minimal offline prompt library and
  expanded it into a usable management workspace backed by sixteen strictly
  validated desktop-to-sidecar commands.
- Added deterministic composition of enabled saved blocks in durable order through
  the existing `PromptBuilder` boundary.
- Added a distinct final-prompt preview and explicitly confirmed execution through
  the host-authored `ups.offline-echo` provider.
- Added bounded non-secret execution metadata plus source, Rust, frontend,
  frozen-sidecar, restart, and installed-layout coverage.
- Added the host-authorized `ups.openai-responses` provider with one fixed HTTPS
  endpoint and a closed model, temperature, and maximum-output-token schema.
- Added a two-provider desktop catalog, availability feedback, explicit provider
  selection, and separately confirmed configured execution and credential clearing.
- Added atomic exact-shape non-secret provider settings below app data while
  preserving SQLite schema 1.
- Added current-user Windows DPAPI credential protection; raw keys are excluded
  from SQLite, settings JSON, web storage, logs, errors, responses, and results.
- Added independent Python, Rust, and frontend validation plus installed restart,
  ciphertext, plaintext-redaction, dependency-audit, and packaging coverage.
- The next checkpoint is A-005: workflow authoring, validation, and bounded
  sequential execution UI.

This changelog records milestone-level changes. Git history remains the source
for checkpoint-level implementation detail.
