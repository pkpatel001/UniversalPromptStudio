# ADR-0019: AI Provider Discovery, Compatibility, and Catalog

**Status:** Accepted  
**Milestone:** E-014.2

## Context

E-014.1 established a strict, portable provider manifest but only inspected one
exact file. Provider generation and application integration need a deterministic
way to locate metadata, retain its source provenance, reject ambiguous
identities, classify SDK compatibility, and resolve providers by version and
capability without importing provider code.

Automatic machine-wide roots or source precedence would introduce hidden state
and trust decisions before installation and configuration policies exist.

## Decision

### Explicit-root discovery

`ProviderDiscoveryService` recursively searches only caller-approved,
stable-labeled roots for the exact filename `ai-provider-manifest.yaml`.
Discovery is sorted and read-only. It does not follow symlinked roots,
directories, or manifests and ignores standard VCS, cache, environment,
dependency, build, distribution, and target directories.

Records and issues retain root ID and portable relative path. Root IDs and
resolved paths must be unique. Missing and symlinked roots are explicit issues.

There are no automatic project, bundled, or per-user roots in E-014.2. CLI
catalog commands require at least one explicit `--root`.

### Duplicate policy

Provider identity is the pair of provider ID and implementation version. The
same pair appearing more than once across any approved roots is an error. Root
order does not establish precedence, and discovery never replaces one provider
with another.

### SDK compatibility

`ProviderSdkContract` defines an inclusive supported API-level range. The
default host range is level 1. Structurally valid metadata outside the range is
classified as `too-old` or `too-new` and excluded from the compatible
catalog while retaining a deterministic issue.

Manifest schema compatibility, provider implementation version, and Provider
SDK API level remain separate concepts.

### Catalog resolution

`ProviderCatalog` accepts compatible records and rejects duplicate identities.
It resolves an exact version or the highest version for a provider ID. Optional
capability requirements use set inclusion against the manifest declarations.
Stable provider ordering and version inventory are available without probing a
service.

Capability matching means metadata declares support. It does not prove model
availability, authorization, service health, or runtime behavior.

### CLI

The accepted E-014.1 exact-file command remains:

```powershell
python -m Engineering provider inspect MANIFEST
```

E-014.2 adds:

```powershell
python -m Engineering provider list --root ROOT
python -m Engineering provider validate --root ROOT
python -m Engineering provider resolve PROVIDER_ID --root ROOT
```

Roots and capability filters are repeatable. Every command is read-only and
non-executing.

## Security boundary

Discovery and resolution do not import entry points, access credentials,
contact providers, enumerate models, or make network requests. Metadata
validity, SDK compatibility, root location, version selection, and capability
matching are not trust or runtime-readiness decisions.

## Consequences

- Later provider scaffolding and integration can consume stable catalog records.
- Multiple explicitly approved roots can be combined without hidden precedence.
- Future SDK levels remain structurally inspectable with explicit compatibility
  results.
- E-014.3 can add controlled provider scaffold generation through E-009/E-008.
- Installation, provider loading, credential resolution, runtime configuration,
  model discovery, health checks, requests, streaming, retries, cancellation,
  and real provider integrations remain deferred.
