# Manifest System

E-012.1 introduced the shared manifest catalog. E-012.2 added explicit schema
contracts, cardinality, and dependency validation. E-012.3 integrates the
historical documentation YAML and adds deterministic, read-only migration
planning.

```text
registered manifest family
    -> deterministic filename discovery
    -> adapter-owned schema detection
    -> schema compatibility classification
    -> producer-owned structural validation
    -> portable path and SHA-256 inventory
    -> cardinality and dependency validation
    -> optional migration planning (no writes)
```

## Supported manifest families

| Stable id | Owner | Filename | Current/readable | Cardinality |
| --- | --- | --- | --- | --- |
| `ups.template-artifact` | E-009 Templates | `.ups-artifact-manifest.json` | 1 / 1 | many |
| `ups.build` | E-010 Build System | `build-manifest.json` | 1 / 1 | one |
| `ups.documentation` | Documentation Generator | `documentation_manifest.yaml` | 1 / 0, 1 | one |
| `ups.release` | E-011 Release System | `release-manifest.json` | 1 / 1 | one |
| `ups.plugin` | E-013 Plugin System | `plugin-manifest.yaml` | 1 / 1 | many |
| `ups.ai-provider` | E-014 Provider System | `ai-provider-manifest.yaml` | 1 / 1 | many |
| `ups.theme` | E-015 Theme System | `theme-manifest.yaml` | 1 / 1 | many |
| `ups.workflow` | E-016 Workflow System | `workflow-manifest.yaml` | 1 / 1 | many |

The shared system does not reinterpret or replace existing JSON producer
payloads. Their adapters call each owner's existing reader. The documentation
adapter owns the legacy YAML contract because the historical generator did not
provide a typed reader.

Documentation schema `0` is reserved for the tracked, unversioned YAML shape.
Schema `1` is the canonical target shape: the same validated payload with a root
`schema_version: 1` field. The documentation generator and its tracked output
remain unchanged in E-012.3, so this transitional compatibility is explicit.

## CLI

```text
python -m Engineering manifest types
python -m Engineering manifest inspect
python -m Engineering manifest inspect --root <directory>
python -m Engineering manifest validate
python -m Engineering manifest validate --root <directory>
python -m Engineering manifest migrations
python -m Engineering manifest migrations --root <directory>
```

Inspection is recursive, deterministic, and read-only. Dependency directories,
tool caches, Rust `target/`, and Git metadata are excluded. Discovered symlinks
are rejected, paths remain relative to the inspection root, and each validated
manifest receives a SHA-256 digest in the in-memory report.

`inspect` validates each document independently. `validate` additionally applies
the registered manifest graph. The built-in graph requires every discovered
`ups.release` manifest to have a discovered `ups.build` manifest and rejects
multiple build, documentation, or release manifests in one inventory. Template
artifact, plugin, AI-provider, theme, and workflow manifests intentionally allow multiple
documents.

## Schema evolution

Each family declares one positive current schema and an ascending set of
readable schemas. Version `0` may appear only as an explicitly registered legacy
schema; it can never be current. A document is classified as:

- `current` when it matches the canonical schema;
- `readable` when an older version remains supported;
- `unsupported` when no registered reader contract covers it.

Schema detection belongs to each adapter. Existing versioned JSON families read
their integer root `schema_version`; the documentation adapter parses YAML and
maps a missing version field to legacy schema `0`.

## Migration planning

Migration registrations are declarative forward-only edges. Each edge identifies
one family, source and target schemas, a stable migration id, and a description.
Registration rejects unknown families, unreadable versions, duplicate ids,
duplicate transitions, and non-forward routes.

`manifest migrations` first performs normal structural inspection, then plans a
shortest deterministic route from every backward-readable document to its
family's current schema. The built-in route is:

```text
ups.documentation 0 -> 1
    add root schema_version: 1
    preserve the validated manifest payload
```

A missing route is a validation failure. Current manifests require no plan.
Plans exist only in memory: the command has no apply mode, transformation
callback, filesystem writer, or persistence side effect.

## Boundary

The closed toolkit catalog covers all current producer families, including
workflow manifests. It validates legacy documentation manifests and plans safe
schema upgrades, but does not rewrite tracked YAML, change generators, execute
migrations, sign manifests, or orchestrate persistence. Those actions require
a separate reviewed checkpoint.
