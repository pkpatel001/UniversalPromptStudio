# ADR-0014: Plugin Discovery, Compatibility, and Dependency Hardening

**Status:** Accepted  
**Milestone:** E-013.2

## Context

E-013.1 established a safe schema-1 plugin manifest, single-root discovery, and
basic ID/version catalog resolution. It deliberately treated dependencies and
permissions as metadata and accepted only the current SDK API level in the
reader.

Before scaffold generation or any runtime design, the metadata layer needs to
answer four questions deterministically:

1. How can callers inspect more than one explicitly approved root without
   silently replacing duplicate plugins?
2. How is a structurally valid manifest distinguished from a plugin compatible
   with this host?
3. How are declared dependencies evaluated against the locally discovered
   catalog without installing anything?
4. How does the catalog select versions consistently for dependency consumers?

## Decision

### Root-labeled discovery

A `PluginDiscoveryRoot` contains a stable metadata ID and a filesystem path.
The discovery service accepts one or more explicitly approved roots, sorts them
by ID, and records the root ID on every record and issue.

Root IDs and resolved paths must both be unique. Missing or symlinked roots are
aggregated as `plugin.root.missing` or `plugin.root.symlink`. Existing
exact-filename matching, ignored-directory policy, resolved-path containment,
manifest symlink rejection, and non-execution guarantees remain unchanged.

Duplicate plugin ID/version pairs across any roots are errors. E-013.2 does not
introduce source precedence or replacement semantics. The CLI defaults to the
project `Plugins/` root and supports repeatable `--root` options labeled in
argument order. Automatic bundled and per-user root location policy remains
deferred to installation and trust planning.

### Compatibility is separate from parsing

`PluginManifestReader` validates that `sdk_version` is a positive integer but
does not reject a future API level. This allows tools to inspect and explain
structurally valid future metadata.

`PluginSdkContract` owns the inclusive host-supported API-level range. It
classifies plugins as `compatible`, `too-old`, or `too-new`. The current
default contract supports level 1 only. Incompatibility produces
`plugin.sdk.incompatible`.

Catalog registration rejects incompatible records. Dependency analysis runs
only after structural discovery and compatibility succeed, preventing
cascading missing-dependency noise from invalid or incompatible manifests.

### Installed-metadata dependency resolution

Dependency analysis is read-only. For every compatible plugin record, the
resolver evaluates each PEP 440 constraint against compatible records already
present in the catalog:

- no discovered ID produces `plugin.dependency.missing`;
- discovered versions with no constraint match produce
  `plugin.dependency.unsatisfied`;
- a satisfied constraint selects the highest matching version; and
- cycles among selected ID/version nodes produce
  `plugin.dependency.cycle`.

Pre-release matching is explicit and deterministic. Resolutions are stable
records containing owner ID/version/root/path, requested dependency and
specifier, and selected version. Cycle messages use a canonical rotation so the
same graph produces the same issue.

The resolver does not download, install, activate, or import dependencies. It
does not solve a global package-installation constraint problem. Each declared
edge is evaluated against the current compatible catalog.

### Catalog and reporting

`PluginCatalog` now:

- rejects incompatible SDK records;
- lists all versions for a plugin ID in deterministic order;
- preserves exact and highest-version resolution; and
- resolves the highest version satisfying a PEP 440 specifier.

`PluginValidationReport` combines compatible records, dependency selections,
and stable issues. Structural issues stop compatibility and dependency phases;
compatibility issues stop dependency analysis.

The read-only CLI adds:

```text
python -m Engineering plugin dependencies [--root PATH ...]
```

`plugin list`, `plugin inspect`, and `plugin validate` now use comprehensive
compatibility and dependency validation. They display root provenance and
selected dependency versions.

## Security boundary

- No entry point is imported or resolved.
- No plugin or dependency code is executed.
- No network access, package download, installation, or filesystem mutation is
  performed.
- Multi-root inspection requires explicit caller-provided paths.
- Root labels provide provenance but do not imply trust.
- Compatibility means only SDK API-level compatibility, not safety or trust.
- Dependency satisfaction means only that matching metadata is present.

## Consequences

- Future scaffold generation can target a dependency-coherent metadata model.
- Future installation and runtime work can reuse stable root provenance,
  compatibility results, and dependency selections.
- Catalog ambiguity and cross-root shadowing remain explicit failures.
- E-013.3 scaffold generation, E-013.4 install/trust planning, and E-013.5
  runtime loading remain separate checkpoints.
