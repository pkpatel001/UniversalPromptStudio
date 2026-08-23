# Plugin System

E-013 defines the metadata contract for UPS plugins. It safely parses, validates,
discovers, and catalogs exact `plugin-manifest.yaml` files without importing or
executing their entry points.

The subsystem owns plugin identity, restricted canonical PEP 440 versions with
three release components, SDK API-level compatibility, entry-point syntax,
capabilities, permission requests, and plugin dependency constraints.
Capabilities and permissions are metadata only.

E-013.2 adds stable root provenance, explicit multi-root aggregation, SDK
compatibility classification, constrained dependency selection, cycle
detection, and compatibility-aware catalogs. Dependency resolution inspects
only already-discovered metadata; it never installs or downloads anything.

E-013.3 adds controlled project-local scaffold generation. The Plugin System
validates plugin-owned inputs and composes the built-in `plugin.python-basic`
E-009 template. E-009 resolves variables and records the artifact manifest;
E-008 owns rendering, destination safety, conflicts, dry runs, and writes.
Scaffolds are restricted to one direct child of `Plugins/`.

E-013.4 defines the canonical `.ups-plugin.zip` package boundary and adds
read-only package inspection plus installation planning. Archive members are
bounded, hashed, path-checked, and never extracted. Planning requires an
explicit matching SHA-256 approval, validates the approved local root, SDK
compatibility, identity conflicts, and dependencies, then reports a target and
issues without changing the filesystem. The hash approval is ephemeral and is
not a signature, publisher identity, trust-store record, or code-safety claim.

E-013.5 adds an explicit trusted runtime for project-local source directories.
It hashes one bounded immutable directory snapshot, requires an exact ephemeral
digest approval plus a full-trust acknowledgment, loads source bytes under a
private namespace through a replaceable loader interface, and provides typed
activation/deactivation with scoped transactional contributions. Activation
failure rolls back registrations and modules; deactivation always clears
host-owned contributions and loader state.

This fast-track loader runs in the host process and is not a sandbox. A plugin
has the host's operating-system and Python authority. Plugins with permission
requests are blocked because permissions cannot be enforced. Loading is never
automatic, and trust is never persisted.

Installation, permission enforcement, process or OS isolation, signature
verification, trust persistence, archive extraction, updates, removal, remote
synchronization, and marketplace behavior remain outside this checkpoint.
