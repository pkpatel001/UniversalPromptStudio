# Known limitations

## Product integration

- A-002.2 provides project-owned prompt editing, ordered blocks, categories,
  tags, deterministic project-scoped search, and explicit prompt/project
  deletion under Tauri's per-user app-data directory.
- The product bundles and verifies the Windows x86_64 Python sidecar. Other target
  triples still require platform-native locked builds and acceptance evidence.
- Search is a bounded synchronous scan of the selected local project; there is no
  background index, ranking, fuzzy matching, or cross-project search.
- Prompt composition uses only enabled saved blocks in durable order. There are no
  variables, attachments, conditional blocks, or unsaved-draft previews.
- Execution is limited to the bundled `ups.offline-echo` provider with no options;
  provider selection, endpoints, credentials, models, and network calls are deferred.
- Execution results and metadata are not persisted after the process exits.
- Deleted projects and prompts are not recoverable in the application UI.
- Workflow authoring and execution have no product UI.

## Extensibility and trust

- Trusted plugins and host-created provider/workflow handlers execute in process;
  they are not sandboxed.
- Plugin permissions cannot be enforced and permission-requesting plugins are
  blocked.
- Exact SHA-256 approval proves byte identity, not publisher identity or safety.
- Cryptographic signatures, persisted trust, remote revocation, automatic
  updates, and marketplaces are deferred.
- External AI endpoints, credential resolution, model discovery, streaming,
  cancellation, retries, and health checks are deferred.

## Themes and workflows

- Themes use a fixed semantic color set; custom CSS, fonts, icons, assets, and
  automatic contrast auditing are unsupported.
- Workflow schema 1 is a bounded DAG executed sequentially. Cycles, conditions,
  parallelism, retries, scheduling, persistence, and external handler loading
  are unsupported.

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
