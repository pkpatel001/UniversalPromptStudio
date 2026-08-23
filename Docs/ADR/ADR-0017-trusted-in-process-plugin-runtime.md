# ADR-0017: Trusted In-Process Plugin Runtime

**Status:** Accepted  
**Milestone:** E-013.5

## Context

E-013.4 established a bounded package format, exact package-hash approval, and
non-mutating installation planning. The Engineering Toolkit now needs a real
lifecycle contract before moving to later roadmap areas.

A subprocess design would add IPC contracts, serialization, worker supervision,
Windows process handling, and error transport. It would slow this checkpoint
without itself providing an operating-system sandbox. The project schedule
favours a smaller runtime that is honest about its authority while preserving a
replacement boundary for stronger isolation later.

## Decision

### Explicit project-local scope

E-013.5 loads only a plugin already present below one explicitly selected local
discovery root. It does not extract a package, install code, search remote
sources, persist approval, or load anything automatically at startup.

The runtime validates the complete root catalog, SDK level, and dependency
graph. Runtime dependencies must already be active at their selected versions;
the manager never auto-activates them.

### Exact snapshot approval

`PluginDirectorySnapshotter` captures one bounded immutable byte snapshot of
the selected plugin directory. Unsafe, symlinked, ambiguous, excluded, or
oversized content is rejected. A versioned deterministic SHA-256 covers every
accepted relative path, length, and byte payload.

The manifest parsed from snapshot bytes must equal the manifest selected during
validation. The caller supplies an exact ephemeral directory digest and
explicitly acknowledges full trust. A missing acknowledgment or identity/hash
mismatch blocks loading before plugin code executes.

The snapshot bytes, not a second filesystem read, supply the Python source to
the loader. This ties approval and entry-point loading to the same revision.

### Replaceable trusted loader

`PluginModuleLoader` separates lifecycle orchestration from loading strategy.
E-013.5 provides `TrustedInProcessLoader`. It uses a private synthetic module
namespace, does not persistently modify `sys.path`, supports dotted entry
points and relative imports from snapshot bytes, and removes its finder and all
private modules on unload.

This loader is not a sandbox. Plugin code executes in the host process with the
host user's full Python and operating-system authority. Exact hashes establish
integrity only, not publisher identity, provenance, review, or safety.

### Lifecycle and contributions

Entry points structurally implement:

```text
activate(PluginRegistrationContext) -> None
deactivate(PluginRegistrationContext) -> None
```

Observable states are `approved`, `loading`, `active`, `unloading`,
`inactive`, and `failed`.

The registration context accepts only manifest-declared capability IDs and
unique contribution IDs. Contributions are staged during activation and commit
atomically only after activation succeeds. Activation failure discards staged
contributions and unloads the private namespace.

Deactivation calls plugin cleanup, then clears host-owned contributions and
loader state regardless of plugin failure. A cleanup failure ends in `failed`.
Loaded and unloaded events publish only after successful transitions.

### Permission policy

Permission labels are still not enforceable. Rather than presenting metadata as
security, the runtime blocks every manifest with a non-empty `permissions`
list. Supporting such plugins requires a future enforceable isolation and
permission design.

### CLI

```powershell
python -m Engineering plugin runtime digest PLUGIN_ID
python -m Engineering plugin runtime probe PLUGIN_ID --approve-sha256 SHA256 --acknowledge-full-trust
```

`digest` validates and snapshots without importing code. `probe` explicitly
activates and then deactivates one plugin inside that CLI process. Neither
command persists trust or runtime configuration.

## Consequences

- The Engineering Toolkit gains a real, typed, transactional plugin lifecycle
  with substantially less implementation overhead than a worker architecture.
- Native Python contribution objects require no IPC serialization.
- The loader abstraction preserves a migration path to subprocess or
  OS-sandboxed execution.
- Plugins must be treated as fully trusted application code.
- There is no containment if trusted plugin code is malicious or compromised.
- Automatic loading, installation, persisted trust, permission enforcement,
  signatures, publisher identity, revocation, remote sources, marketplace
  behavior, and process or OS isolation remain deferred.
