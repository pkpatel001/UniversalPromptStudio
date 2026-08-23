# ADR-0012: Safe Manifest Migration Planning

**Status:** Accepted  
**Milestone:** E-012.3

## Context

The repository contains a generated `documentation_manifest.yaml` that predates
E-012 and has no schema-version field. E-012.2 intentionally excluded this YAML
because its generic envelope reader assumed versioned JSON and because silently
rewriting generated documentation would cross a producer-ownership boundary.

The manifest system needs to inventory this real legacy document and describe a
safe route toward an explicit schema without mutating it, changing the generator,
or claiming that a migration succeeded before an execution design exists.

## Decision

### Legacy documentation contract

Register `documentation_manifest.yaml` as the singleton
`ups.documentation` family. Its adapter owns YAML parsing and validates:

- a mapping root containing the legacy `manifest` payload;
- non-empty `generated_by` and portable relative `output_root` values;
- document entries with non-empty identifiers, relative paths, and titles;
- optional failed entries with identifiers, relative paths, and reasons;
- uniqueness of document identifiers and paths.

An absent root `schema_version` is classified as legacy schema `0`. An explicit
integer `schema_version: 1` is the canonical target contract. Version `0` is
allowed only as a readable legacy version and can never be a family's current
schema. This narrow exception supersedes ADR-0011's blanket rejection of
non-positive readable versions.

Schema detection moves behind the adapter interface. Existing JSON adapters keep
the same version-envelope behavior, while the documentation adapter can recognize
its historical YAML without weakening the other families.

### Planning contract

A `ManifestMigrationStep` is metadata, not executable code. It declares a stable
id, one manifest family, a forward source-to-target transition, and a human
review description. Registration validates that both versions are readable for
the family and rejects duplicate, backward, self, or unknown transitions.

The planner considers only structurally valid records classified as `readable`.
It finds the shortest route to the family's current schema with stable ordering.
If no route exists, the planner produces `manifest.migration.unavailable`; current records need no plan.
Inspection problems are retained in the aggregate migration report.

The initial registered step is:

```text
ups.documentation.v0-to-v1
ups.documentation schema 0 -> 1
Add root schema_version: 1 while preserving the validated manifest payload.
```

### Non-mutation boundary

`python -m Engineering manifest migrations` reports plans and steps. E-012.3
provides no apply command, payload transformer, write callback, backup policy, or
persistence workflow. The documentation generator and tracked generated manifest
remain unchanged. Tests compare the manifest bytes before and after planning.

## Consequences

- The existing documentation manifest participates in normal discovery,
  compatibility classification, hashing, and cardinality validation.
- Consumers can see a precise, reviewable upgrade route without conflating a plan
  with execution.
- Future multi-step migrations can be registered without changing discovery.
- YAML parsing remains isolated to the documentation owner adapter.
- Migration execution, backup/rollback design, generator cutover, signing, and
  persistence remain future decisions.
