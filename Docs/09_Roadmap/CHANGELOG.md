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
- Added the schema-1 workflow studio for bounded workflow identity, typed
  boundary ports, trusted operation nodes, directed edges, deterministic plan
  feedback, runtime inputs, step progress, intermediate values, and final output.
- Added atomic exact-shape workflow-definition persistence below application
  data while retaining SQLite schema 1 and ephemeral execution outcomes.
- Added eight fixed workflow commands with independent frontend, Rust, and
  Python validation for definitions, trusted operation contracts, plans,
  confirmations, sequential steps, runtime values, and safe failures.
- Added the host-owned saved-prompt workflow operation, which reuses durable
  project/prompt ownership and the existing offline/configured provider boundary
  without transporting credentials, endpoints, options, or arbitrary prompt text.
- Added source, frozen-sidecar, restart, and installed-layout workflow
  persistence/planning/execution coverage.
- Added independent Python, Rust, and frontend validation plus installed restart,
  ciphertext, plaintext-redaction, dependency-audit, and packaging coverage.
- Added managed theme inbox/install/disable/restore UI with exact package digests,
  fail-closed semantic token transport, and explicit trust review.
- Added permissionless extension catalog and digest-bound session activation;
  restart clears approval and contributions.
- Added atomic non-secret application settings, compact layout, reduced motion,
  and first-run onboarding with fixed telemetry/update policy.
- Added bounded single-prompt and single-workflow JSON export, previewed import,
  explicit conflict resolution, digest binding, and confirmation.
- Added presentation-safe diagnostics plus reviewed, digest-bound support export
  that excludes credentials, user content, paths, environment values, and
  extension code.
- Added eight fixed A-007 commands with independent Python, Rust, and frontend
  validation plus frozen-process restart and portability acceptance coverage.
- Added a fixed 15-topic offline Help catalog with deterministic local search,
  safe text-node rendering, related-topic navigation, and responsive native-dialog
  behavior.
- Added contextual task guidance for prompt blocks, composition and provider runs,
  workflows, managed customization, portability, and settings/support without new
  IPC, network, filesystem, storage, or extension authority.
- Added a comprehensive beginner user guide covering Windows installation, first
  use, prompt design, providers, workflows, portability, trust, diagnostics,
  stress testing, troubleshooting, privacy, limitations, and terminology.
- Completed the approved A-001 through A-008 alpha application sequence; further
  product work requires a new explicit checkpoint.

This changelog records milestone-level changes. Git history remains the source
for checkpoint-level implementation detail.
