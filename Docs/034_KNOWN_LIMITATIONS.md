# Known limitations

## Product integration

- A-008 provides project-owned prompt editing, ordered blocks, categories,
  tags, deterministic project-scoped search, and explicit prompt/project
  deletion plus bounded schema-1 workflow authoring, planning, persistence, and
  explicit sequential execution under Tauri's per-user app-data directory.
- The product bundles and verifies the Windows x86_64 Python sidecar. Other target
  triples still require platform-native locked builds and acceptance evidence.
- Search is a bounded synchronous scan of the selected local project; there is no
  background index, ranking, fuzzy matching, or cross-project search.
- Prompt composition uses only enabled saved blocks in durable order. There are no
  variables, attachments, conditional blocks, or unsaved-draft previews.
- Execution supports only `ups.offline-echo` and `ups.openai-responses`. The
  OpenAI endpoint and option names are fixed; there is no model discovery,
  arbitrary compatible endpoint, custom header, OAuth, or other provider.
- Credential protection is Windows-only and uses current-user DPAPI. It does not
  protect against malicious code already running as that user.
- Execution results and metadata are not persisted after the process exits.
- Deleted projects and prompts are not recoverable in the application UI.

## Extensibility and trust

- Trusted plugins and host-created provider/workflow handlers execute in process;
  they are not sandboxed.
- Plugin permissions cannot be enforced and permission-requesting plugins are
  blocked.
- Exact SHA-256 approval proves byte identity, not publisher identity or safety.
- Cryptographic signatures, persisted trust, remote revocation, automatic
  updates, and marketplaces are deferred.
- Additional AI endpoints, authentication schemes, model discovery, streaming,
  cancellation, retries, and health checks are deferred.

## Themes and workflows

- Themes use a fixed semantic color set; custom CSS, fonts, icons, assets, and
  automatic contrast auditing are unsupported.
- Workflow schema 1 is a bounded DAG executed sequentially from an explicit
  valid plan. Definitions persist locally, but runs and values do not. Dynamic
  or plugin-supplied handlers, arbitrary operation IDs, cycles, conditions,
  parallelism, retries, cancellation, scheduling, resume, history, sync, remote
  triggers, and external handler loading are unsupported.

## Portability and support

- Portable files contain exactly one prompt or workflow; bulk backup/restore and
  arbitrary archives or destinations are unsupported.
- Prompt imports target the currently open project. Identity conflicts require an
  explicit create, replace, or keep decision; cross-project identities are not moved.
- Support diagnostics contain counts and states only. They cannot diagnose
  content-specific failures and never include credentials, user content, paths,
  environment values, or extension code.
- Telemetry, automatic upload, cloud sync, localization beyond fixed English, and
  automatic updates are unsupported.
- In-app Help is a fixed English-only offline catalog. It has no screenshots,
  interactive walkthrough automation, remote content updates, or content-specific
  diagnostic access.

## Packaging

- Windows NSIS output is unsigned.
- Publishing, signing, updater metadata, MSI packaging, Git tags, and GitHub
  Releases are outside the local release system.
- Platform-specific packaging requires its external toolchain to be installed
  beforehand.

## Self-generation

- Self-generation supports only an allowlisted Engineering subsystem scaffold.
- It cannot select arbitrary paths, templates, commands, imports, overwrite
  behavior, commits, pushes, releases, or dependency installation.

See `Docs/09_Roadmap/ENGINEERING_TOOLKIT_CAPABILITY_MATRIX.md` for the complete
supported/deferred matrix.
