# Provider registries

UPS uses two registries with separate responsibilities.

`Engineering.ProviderSystem.ProviderRuntimeRegistry` binds an exact validated
provider record to an already-created runtime implementation. It enforces SDK
compatibility, the `text-generation` capability, and exact provider ID/version
matching. Duplicate identities fail. Resolution selects an exact version or
the highest registered version; unregistration is explicit. It does not import,
instantiate, configure, or invoke providers.

`Backend.core.registry.ProviderRegistry[AIProvider]` is the phase-one
application registry. It resolves an application-facing provider by normalized
name. E-014.6 registers both `dummy` and the SDK-backed `ups.offline-echo`
adapter. Existing replace-by-name behavior is retained for compatibility and
must not be confused with the stricter SDK runtime registry.

`ProviderExecutionService` invokes a selected SDK runtime once. The Backend
`ProviderRuntimeAIAdapter` translates between SDK and application request,
result, and failure contracts. The application service remains unaware of SDK
metadata and continues to use the `AIProvider` interface.

There is no automatic priority or fallback policy. Highest-version selection
occurs only inside the SDK runtime registry when a caller omits a version. The
built-in offline provider is explicitly pinned to version `1.0.0` by the
composition root.

Discovery catalogs are read-only metadata inventories and do not populate
either runtime registry automatically. Arbitrary manifest entry points remain
non-executable until a later loading and trust design is approved.
