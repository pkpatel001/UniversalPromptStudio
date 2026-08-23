# ADR-0021: Typed AI-provider runtime and controlled registration

## Status

Accepted

## Context

E-014.1 through E-014.3 established strict provider metadata, compatible
catalog resolution, and controlled passive scaffolds. The toolkit still lacked
a stable request, response, and failure vocabulary for provider authors. It
also lacked a safe way for a future composition root to associate a validated
manifest record with an already-created runtime instance.

Loading entry points, resolving credentials, contacting services, and executing
requests have materially different trust and operational risks. Defining those
behaviors in the same checkpoint would blur the accepted metadata boundary.

## Decision

E-014.4 defines a minimal immutable text-generation API:

- `ProviderTextRequest` carries a correlated request ID, prompt, optional model,
  and immutable scalar options;
- `ProviderTextResponse` carries correlated text and optional usage;
- `ProviderFailure` carries a stable failure code, safe message, and retryable
  classification; and
- `RuntimeTextProvider` structurally exposes exact provider identity/version
  and a future `generate_text` operation.

Portable request options reject duplicate and credential-like names. This keeps
credentials out of request payload configuration without claiming to provide
credential storage or redaction.

`ProviderRuntimeRegistry` is host-owned and receives an already-instantiated
provider plus a validated `ProviderRecord`. Registration requires SDK
compatibility, a declared `text-generation` capability, and exact runtime-to-
manifest ID/version equality. Duplicate bindings are errors rather than
replacement. Resolution is deterministic and supports exact or highest
registered versions; unregistering is explicit.

Registration performs no entry-point resolution, import, instantiation, method
invocation, network request, or credential access. No CLI command is added
because there is no approved loading or execution path in this checkpoint.

The existing `Backend.interfaces.AIProvider` and application execution service
remain unchanged until a later integration checkpoint defines orchestration and
compatibility behavior.

## Consequences

- Provider authors and future host adapters have stable typed values without
  coupling the SDK to the current application request models.
- Manifest capability, SDK, and identity claims are enforced when a host binds
  an instance.
- Registration cannot silently replace an existing provider or trigger code.
- Failure codes classify outcomes but do not implement retry, timeout, or
  cancellation policies.
- Provider loading, trust approval, runtime configuration, endpoints,
  credentials, request execution, streaming, retries, cancellation mechanics,
  health checks, model discovery, and real integrations remain deferred.
