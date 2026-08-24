# ADR-0033: Workflow discovery, compatibility, catalog, and graph hardening

**Status:** Accepted
**Milestone:** E-016.2

## Context

E-016.1 can validate one passive workflow definition but does not define where
multiple workflows come from, how incompatible SDK levels are classified, how
duplicates are handled, or which records enter a deterministic catalog.
Unbounded or implicit discovery would create resource, precedence, provenance,
and symlink risks.

## Decision

Workflow discovery operates only on explicitly supplied, stable-labeled roots
and the exact 'workflow-manifest.yaml' filename. It sorts roots and paths,
retains root ID and portable relative-path provenance, rejects symlinked roots
and manifests, prunes symlinked directories, and ignores dependency, cache,
VCS, build, distribution, and Rust target directories.

Each root is capped at 16 directory levels, 1,024 workflow manifests, and one
MiB per manifest. Exceeding a bound produces a stable issue and prevents catalog
admission.

Duplicate workflow ID/version pairs are rejected across all roots. Multiple
versions of one workflow ID remain valid. Root order never selects a winner.

The current host accepts Workflow SDK API level 1. Other positive levels can be
structurally inspected but are classified as too old or too new and excluded
from compatible records.

The catalog accepts compatible records only, orders them deterministically, and
resolves an exact version or the highest semantic version. Optional operation
filters match only the closed set of operation IDs declared by nodes.

Schema-1 graph validation additionally rejects unused workflow inputs and nodes
that cannot reach a workflow output. Existing exact reference, type, single
target binding, complete input/output binding, and global cycle checks remain
producer-owned.

The passive CLI adds 'workflow list' and 'workflow validate', both requiring at
least one explicit '--root'.

## Trust boundary

Discovery, compatibility, graph validation, catalog construction, filtering,
and CLI reporting do not import operations, register handlers, plan execution,
execute nodes, access credentials, contact services, launch subprocesses, or
write files. An operation ID match is metadata, not proof that an implementation
exists or is trusted.

## Consequences

- Workflow inventories have deterministic ordering and portable provenance.
- Resource and symlink boundaries are explicit and tested.
- Duplicate identities and incompatible SDK levels fail closed.
- E-016.3 can generate a canonical scaffold through E-009/E-008 and verify it
  through the same producer-owned reader and catalog rules.
- Planning, registration, execution, persistence, retries, branches,
  scheduling, and UI integration remain deferred.
