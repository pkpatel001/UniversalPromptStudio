# ADR-0011: Manifest Schema Contracts and Relationships

**Status:** Accepted  
**Milestone:** E-012.2

## Context

E-012.1 can discover and structurally validate heterogeneous manifests, but a
tuple of supported version numbers does not say which version is current or how
an older readable version should be classified. Independent validation also
cannot detect an incoherent set, such as release metadata without evidence of a
successful build or multiple singleton manifests in one inventory.

The manifest system needs explicit evolution and relationship rules without
taking ownership of producer payloads or silently rewriting files.

## Decision

### Schema contracts

Every `ManifestSpec` exposes a `ManifestSchemaContract` containing:

- the current producer schema version;
- the ascending set of readable versions;
- deterministic classification as `current`, `readable`, or `unsupported`.

The registry rejects non-positive, duplicate, unordered, and ambiguous version
declarations. The current version must be the latest readable version. Generic
envelope validation reads `schema_version` before delegating payload semantics to
the producer adapter, allowing unsupported and malformed schemas to receive
stable issue codes.

No migration is performed. A future producer may retain an older version in its
readable set only while its adapter can actually parse that version.

### Manifest relationships

Each family declares whether multiple documents may appear in one inventory.
Template artifact manifests are plural; build and release manifests are
singletons.

Typed `ManifestDependency` edges define required cross-family relationships.
The built-in graph states:

```text
ups.release -> requires ups.build
```

Dependency registration rejects unknown families, self-references, duplicate
edges, and cycles. Validation is deterministic and reports missing dependencies
and excess singleton documents without modifying the filesystem.

### Command boundary

`manifest inspect` remains independent document inspection. `manifest validate`
adds cardinality and dependency checks to the structurally valid inventory. If
structural inspection fails, graph validation is skipped to prevent cascading
missing-dependency noise.

## Consequences

- Consumers can distinguish current documents from intentionally readable older
  schemas.
- Future schema evolution has an explicit compatibility declaration.
- Release inventories cannot appear coherent without a build manifest.
- Multiple generated template destinations remain supported.
- Producer readers continue to own payload meaning.
- Automatic migration, YAML conversion, signing, and persistence remain outside
  E-012.2.
