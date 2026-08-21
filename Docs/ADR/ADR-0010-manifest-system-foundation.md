# ADR-0010: Manifest System Foundation

**Status:** Accepted  
**Milestone:** E-012.1

## Context

E-009, E-010, and E-011 each produce deterministic manifests, but discovery and
validation remain accessible only through their owning subsystems. Later plugin,
provider, theme, and workflow milestones need a stable way to identify manifest
families without importing CLI code or inventing another artifact model.

A shared system must preserve the existing ownership boundary: templates define
template artifact semantics, builds define build semantics, and releases define
release semantics.

## Decision

Introduce `Engineering.ManifestSystem` as a typed, read-only catalog.

- `ManifestSpec` identifies a family by stable id, exact filename, kind, and
  supported schema versions.
- `ManifestRegistry` rejects duplicate ids and filenames and resolves adapters
  deterministically.
- Built-in adapters delegate structural validation to the existing E-009,
  E-010, and E-011 readers.
- `ManifestInspectionService` recursively discovers exact registered filenames,
  rejects unsafe symlinked files, retains portable relative paths, and records a
  SHA-256 digest for every valid manifest.
- Inspection aggregates invalid manifests instead of stopping at the first
  producer error.
- The `manifest types` and `manifest inspect` commands are presentation-only
  adapters over the domain service.

The scanner excludes Git metadata, dependency trees, tool caches, virtual
environments, and Rust build output. Inspection never writes or repairs files.

## Consequences

- Existing manifest producers retain their established formats and behavior.
- Later systems can register new manifest families through one typed boundary.
- CI and developers can inventory heterogeneous manifests with a single command.
- Legacy `documentation_manifest.yaml` is not silently treated as a versioned
  E-012 document; any migration requires a separate schema decision.
- Schema migration, cross-manifest dependency validation, and unified persistence
  are intentionally deferred to later E-012 checkpoints.
