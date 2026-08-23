# ADR-0022: Controlled AI-provider invocation

## Status

Accepted

## Context

E-014.4 defined typed text request, response, and failure values and allowed a
host to bind validated provider metadata to an already-created implementation.
It deliberately did not invoke provider code. The SDK now needs a single,
testable boundary for future hosts to call an explicit registration without
embedding selection, exception, and result-validation behavior throughout the
application.

Provider loading, credentials, network configuration, retries, cancellation,
and application integration require separate policy. Pulling them into the
first invocation boundary would unnecessarily expand both authority and scope.

## Decision

E-014.5 adds `ProviderExecutionService` and immutable
`ProviderExecutionReport`.

The service:

1. accepts only a typed request and resolves an exact or highest explicitly
   registered provider version;
2. rechecks runtime identity/version immediately before invocation;
3. calls `generate_text` exactly once;
4. accepts only a typed response or failure whose request ID matches; and
5. returns the exact resolved provider identity/version with the outcome.

A valid structured provider failure is preserved. Identity drift, provider
exceptions, invalid result types, and request-correlation failures become a
non-retryable `provider-error`. Exception type and text are intentionally not
included in the returned message. Unknown providers and invalid host arguments
remain host-side `ProviderError` values because invocation did not begin.

The service receives an existing registry and performs no discovery, import,
entry-point resolution, instantiation, configuration, credential access,
network request, retry, cancellation, streaming, or Backend adaptation. No CLI
command is added because the toolkit has no approved provider loader.

## Security boundary

Invocation is not sandboxed. An implementation supplied by trusted host
composition executes in-process with the host's Python and operating-system
authority. The service contains ordinary Python exceptions at its API boundary
but cannot prevent provider code from accessing resources. Registration and
invocation must therefore remain limited to explicitly trusted instances until
a stronger isolation and trust design exists.

## Consequences

- Future application adapters gain one deterministic invocation boundary.
- A provider is called no more than once per service call; retryable is data,
  not automatic behavior.
- Provider result correlation and shape are enforced centrally.
- Raw exception text does not leak through the portable failure contract.
- Loading, trust approval, runtime configuration, endpoints, credentials,
  streaming, retry policy, cancellation mechanics, health checks, model
  discovery, Backend integration, and real providers remain deferred.
