# Known limitations

## Product integration

- A-001.1 readiness IPC works only in debug development builds with the fixed
  system-Python command and compile-time repository root. Release builds fail
  closed until A-001.2 bundles the sidecar/runtime.
- Prompt/project persistence and search are not exposed as complete desktop
  workflows.
- Prompt builder editing and execution controls remain mostly static shell UI.
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
