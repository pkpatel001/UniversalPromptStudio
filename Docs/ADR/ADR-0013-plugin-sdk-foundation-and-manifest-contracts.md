# ADR-0013: Plugin SDK Foundation and Manifest Contracts

**Status:** Accepted  
**Milestone:** E-013.1

## Context

Universal Prompt Studio needs plugin generation, controlled loading, installation,
trust, and marketplace behavior in later checkpoints. Those systems require a
stable identity and metadata contract first. The existing
`Backend.interfaces.Plugin` abstraction is a placeholder runtime activation
interface; it is not a manifest schema, discovery policy, or SDK compatibility
contract.

E-008 and E-009 already own safe generation and templates. E-012 already owns
shared manifest discovery, compatibility classification, and cardinality.
E-013.1 must add plugin-owned meaning without duplicating those systems or
executing untrusted code.

## Decision

### Domain boundary

`Engineering.PluginSystem` owns immutable plugin metadata models, schema-1 YAML
parsing, validation, bounded discovery, duplicate detection, and catalog
resolution. Parsing a valid manifest states only that its metadata conforms to
the schema. It does not establish trust or runtime safety.

`Backend.interfaces.Plugin` remains unchanged for this checkpoint. A later
runtime design must reconcile lifecycle, typed registration context, failure
contracts, and deactivation before any module is imported or activated.

### Identity and versions

A plugin ID is 1-128 lowercase characters in at least two dot-separated
segments. Segments begin with a letter and may contain digits and internal
hyphens. Examples are `example.echo` and `com-patel.tools`. IDs are stable and
case-sensitive.

Plugin versions use a restricted canonical PEP 440 contract accepted by
`packaging.version.Version`: exactly `major.minor.patch` release components,
no epoch, and no local version. Pre-release, post-release, and development
segments remain available in canonical PEP 440 form. This restriction prevents
multiple textual release widths from representing the same catalog version and
supplies deterministic ordering.
An omitted version resolves to the highest registered version; an explicit
version requires an exact textual match.

Plugin SDK compatibility is a positive integer API level, not a free-form
version range. Schema 1 supports SDK API level 1 only. A schema change and an SDK
API-level change are separate compatibility decisions.

### Canonical manifest

The exact filename is `plugin-manifest.yaml`. The stable E-012 family ID is
`ups.plugin`, the manifest kind is `plugin`, current/readable schema is 1,
and cardinality is many.

Schema 1 requires exactly these root and plugin keys:

```yaml
schema_version: 1
plugin:
  id: example.echo
  name: Echo Plugin
  version: 1.0.0
  sdk_version: 1
  description: Provides echo contributions.
  entry_point: example_echo.plugin:EchoPlugin
  capabilities:
    - commands
  permissions: []
  dependencies:
    - id: example.base
      version: ">=1,<2"
```

Unknown and missing keys are rejected. YAML is read through the shared safe
filesystem reader and must have a mapping root. Integer fields reject booleans.
Secret-like fields, credentials, arbitrary commands, resource paths, and
machine-local state are not part of schema 1.

The entry point uses `module.path:ClassName` syntax. It is syntax-checked only;
the reader, discovery service, catalog, manifest adapter, and CLI never import,
instantiate, activate, or execute it.

Capabilities and permission requests are sorted metadata identifiers. Permission
presence does not imply enforcement or a grant. Dependencies contain one plugin
ID and one non-empty PEP 440 specifier each; they are normalized and sorted.
Duplicate items, duplicate dependency IDs, and self-dependencies are errors.
Dependency installation and graph resolution are deferred.

### Discovery and catalog

E-013.1 discovers recursively below one explicitly approved root. The CLI
defaults to the tracked project `Plugins/` root and accepts an explicit
`--root` for inspection. Bundled and per-user plugin roots, cross-root
precedence, and installation locations are deferred because they require trust
and deployment policy.

Discovery matches the exact filename, sorts paths, ignores VCS, cache, virtual
environment, dependency, build, distribution, and Rust target directories, and
does not follow symlinked directories. Symlinked manifests are rejected.
Resolved manifest paths must remain below the approved root.

Every duplicate plugin ID/version pair is an error, including duplicates that
would later originate from different roots. No source-precedence rule silently
replaces a plugin. The catalog provides stable listings, exact resolution, and
highest-version default resolution.

### Shared manifest integration

`PluginManifestAdapter` registers `ups.plugin` with E-012 and delegates
schema detection and structural validation to `PluginManifestReader`.
E-012 retains exact-filename discovery, hashing, compatibility classification,
and plural cardinality. No cross-family dependency is added because plugin
metadata does not require a build, release, documentation, or template-artifact
manifest to exist.

The existing `generate plugin` placeholder remains unchanged. Plugin
scaffolding must later compose E-009 `TemplateExecutor` and E-008
`GenerationEngine`.

## Security boundary

- Parsing and discovery are read-only and deterministic.
- Entry points are never imported.
- Absolute paths, traversal paths, shell commands, secrets, and credentials are
  not accepted manifest fields.
- Capabilities and permission requests are descriptive metadata only.
- Valid metadata does not imply trust, isolation, or permission enforcement.
- Errors identify fields and portable discovery-relative paths; they do not
  echo secret values.

## Consequences

- Plugin generation and runtime work now have stable identity, compatibility,
  and manifest targets.
- Existing manifest commands recognize any number of valid plugin manifests.
- The project has a tracked `Plugins/` root without inventing unrelated root
  directories.
- Later work can extend this foundation without replacing E-008, E-009, or
  E-012.
- Runtime loading, activation, deactivation, subprocesses, sandboxing,
  permission enforcement, dependency downloading, installation, updates,
  removal, package archives, signatures, trust stores, remote repositories,
  marketplace synchronization, UI management, and Tauri plugins remain
  explicitly deferred.
