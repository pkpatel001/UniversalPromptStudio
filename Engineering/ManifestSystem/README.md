# Manifest System

E-012.1 introduced a shared, read-only catalog for the versioned JSON manifests
already owned by the template, build, and release systems. E-012.2 adds explicit
schema-evolution contracts and dependency-aware validation across a complete
manifest inventory.

```text
registered manifest family
    -> deterministic filename discovery
    -> schema compatibility classification
    -> producer-owned structural validation
    -> portable path and SHA-256 inventory
    -> cardinality and dependency validation
    -> aggregate validation report
```

## Supported manifest families

| Stable id | Owner | Filename | Current/readable | Cardinality |
| --- | --- | --- | --- | --- |
| `ups.template-artifact` | E-009 Templates | `.ups-artifact-manifest.json` | 1 / 1 | many |
| `ups.build` | E-010 Build System | `build-manifest.json` | 1 / 1 | one |
| `ups.release` | E-011 Release System | `release-manifest.json` | 1 / 1 | one |

The shared system does not reinterpret or replace producer-owned payloads.
Adapters call each owner's existing reader so one subsystem remains responsible
for each schema's meaning.

## CLI

```text
python -m Engineering manifest types
python -m Engineering manifest inspect
python -m Engineering manifest inspect --root <directory>
python -m Engineering manifest validate
python -m Engineering manifest validate --root <directory>
```

Inspection is recursive, deterministic, and read-only. Dependency directories,
tool caches, Rust `target/`, and Git metadata are excluded. Discovered symlinks
are rejected, paths remain relative to the inspection root, and each validated
manifest receives a SHA-256 digest in the in-memory report.

`inspect` validates each document independently. `validate` additionally applies
the registered manifest graph. The built-in graph requires every discovered
`ups.release` manifest to have a discovered `ups.build` manifest and rejects
multiple build or release manifests in one inventory. Template artifact
manifests intentionally allow multiple documents.

## Schema evolution

Each family declares one current schema and an ascending set of readable schema
versions. A document is classified as:

- `current` when it matches the producer's current schema;
- `readable` when an older version remains supported;
- `unsupported` when no registered reader contract covers it.

Registration rejects duplicate, unordered, non-positive, or ambiguous version
contracts. Compatibility classification is read-only; E-012.2 does not rewrite
or migrate documents.

## Boundary

E-012.2 validates schema contracts and cross-manifest dependencies. Legacy
documentation YAML, executable schema migrations, signed manifests, and write
orchestration remain future checkpoints. Existing build, generation, and release
behavior is unchanged.
