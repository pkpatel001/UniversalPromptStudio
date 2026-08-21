# Manifest System

E-012.1 introduces a shared, read-only catalog for the versioned JSON manifests
already owned by the template, build, and release systems.

```text
registered manifest family
    -> deterministic filename discovery
    -> producer-owned structural validation
    -> portable path and SHA-256 inventory
    -> aggregate inspection report
```

## Supported manifest families

| Stable id | Owner | Filename | Schema |
| --- | --- | --- | --- |
| `ups.template-artifact` | E-009 Templates | `.ups-artifact-manifest.json` | 1 |
| `ups.build` | E-010 Build System | `build-manifest.json` | 1 |
| `ups.release` | E-011 Release System | `release-manifest.json` | 1 |

The shared system does not reinterpret or replace producer-owned payloads.
Adapters call each owner's existing reader so one subsystem remains responsible
for each schema's meaning.

## CLI

```text
python -m Engineering manifest types
python -m Engineering manifest inspect
python -m Engineering manifest inspect --root <directory>
```

Inspection is recursive, deterministic, and read-only. Dependency directories,
tool caches, Rust `target/`, and Git metadata are excluded. Discovered symlinks
are rejected, paths remain relative to the inspection root, and each validated
manifest receives a SHA-256 digest in the in-memory report.

## Boundary

E-012.1 inventories schema-versioned JSON manifests. Legacy documentation YAML,
schema migrations, cross-manifest relationships, and write orchestration remain
future E-012 checkpoints. Existing build, generation, and release behavior is
unchanged.
