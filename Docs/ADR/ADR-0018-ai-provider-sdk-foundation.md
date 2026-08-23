# ADR-0018: AI Provider SDK Foundation and Manifest Contract

**Status:** Accepted  
**Milestone:** E-014.1

## Context

Universal Prompt Studio has a minimal synchronous `Backend.interfaces.AIProvider`
and a deterministic dummy implementation. That interface is useful for the
current application shell but does not define stable provider identity,
implementation version, SDK compatibility, capabilities, transport,
authentication shape, discovery metadata, or a generation contract.

Provider runtime work also creates credential and network risks. Portable
metadata must be established without embedding machine-local configuration or
making manifest validation execute provider code.

## Decision

### Producer-owned manifest

`Engineering.ProviderSystem` owns schema 1 of the exact filename
`ai-provider-manifest.yaml`. The root contains `schema_version` and one
`provider` mapping. Every key is required and unknown keys are rejected.

The manifest contains stable provider ID, canonical implementation version,
positive SDK API level, name, description, unresolved Python entry point,
transport shape, authentication shape, and a non-empty set of recognized
capabilities.

### Portable and non-secret

Schema 1 intentionally excludes endpoint URLs, headers, environment-variable
names, model inventories, credential names or values, retry settings, timeouts,
commands, and machine-local paths. Secret-like unknown fields are rejected
explicitly.

Authentication metadata is descriptive only. It does not locate, read, grant,
or validate a credential.

### Capability vocabulary

The initial host vocabulary is text generation, streaming, embeddings, vision,
image generation, audio input, audio output, and tool calling. Unknown values
are rejected so later runtime negotiation has an explicit contract.

### No execution

The manifest reader validates `module.path:ClassName` syntax but never imports
or resolves it. It performs no network access, credential access, model
discovery, runtime compatibility claim, or request execution.

### Shared manifest catalog and CLI

E-012 registers a plural `ups.ai-provider` family and delegates validation to
the provider-owned reader. The read-only command is:

```powershell
python -m Engineering provider inspect MANIFEST
```

The existing backend provider interface is not replaced in E-014.1. Runtime
execution contracts must be reconciled only when their failure, streaming,
cancellation, credential, and transport behavior is defined.

## Consequences

- Provider generation and integration gain stable, validated metadata.
- Multiple provider manifests can be inventoried by the shared E-012 catalog.
- Manifests remain portable and safe to inspect without provider execution.
- E-014.2 can add discovery, SDK compatibility, and deterministic cataloging.
- A later scaffold checkpoint can reuse E-009 and E-008.
- Runtime loading, credential resolution, endpoints, model discovery,
  streaming, retries, cancellation, health checks, provider registration, and
  real service integration remain deferred.
