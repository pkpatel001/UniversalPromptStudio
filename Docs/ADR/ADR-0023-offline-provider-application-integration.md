# ADR-0023: Offline provider application integration

## Status

Accepted

## Context

E-014.1 through E-014.5 established provider metadata, scaffolding, typed
runtime contracts, controlled registration, and single-invocation
orchestration. The SDK remained disconnected from the existing
`Backend.interfaces.AIProvider` application flow, so none of those contracts
were exercised through the real composition root.

The project needs an end-to-end vertical slice without introducing a network
provider, credential management, dynamic imports, or a breaking replacement of
the phase-one application interface.

## Decision

E-014.6 adds a deterministic host-authored runtime named `ups.offline-echo`
version `1.0.0`. Its canonical built-in record declares local transport, no
authentication, and `text-generation`. The implementation performs only local
string construction and character counting.

`Backend.infrastructure.providers.ProviderRuntimeAIAdapter` implements the
existing `AIProvider` ABC and owns translation at the outer infrastructure
boundary:

- application prompt and scalar parameters become a typed SDK request;
- underscores in parameter names normalize to hyphens;
- `model` is extracted as the optional SDK model field;
- successful SDK output becomes `PromptExecutionResult` with correlated
  identity/version/request/usage metadata; and
- structured failures become `AIProviderExecutionError` with stable code and
  retryability.

Normalized duplicate options and credential-like names remain errors. The
adapter verifies that a direct request targets its configured provider.

The application composition root creates the offline runtime, registers its
host-owned record in `ProviderRuntimeRegistry`, creates the controlled execution
service and adapter, and registers the adapter under `ups.offline-echo`. The
legacy `dummy` provider remains registered unchanged.

The container exposes the SDK runtime registry for explicit host composition.
`PromptExecutionService`, history behavior, events, presentation callers, and
the generic application provider registry retain their existing contracts.

## Security boundary

The offline reference provider does not read files or environment values,
resolve credentials, or contact a network. No manifest entry point is loaded.
The adapter still invokes in-process Python and is not a sandbox; only trusted
host-created instances may enter the runtime registry.

## Consequences

- The provider SDK is exercised through a complete offline application slice.
- Clean Architecture is preserved: application services depend on `AIProvider`,
  while the infrastructure adapter depends on the provider SDK.
- The dummy path remains available, avoiding a compatibility break.
- The two registries retain explicit, documented semantics rather than being
  merged prematurely.
- Dynamic loading, provider trust persistence, endpoints, credentials, remote
  services, model discovery, health checks, streaming, retries, cancellation,
  UI selection, and real provider integrations remain deferred.
