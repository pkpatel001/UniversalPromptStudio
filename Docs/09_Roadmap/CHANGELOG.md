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
  expanded it into a usable management workspace backed by ten strictly
  validated desktop-to-sidecar commands.
- The next checkpoint is A-003: prompt composition and offline reference execution.

This changelog records milestone-level changes. Git history remains the source
for checkpoint-level implementation detail.
