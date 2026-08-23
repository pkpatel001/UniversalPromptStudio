# AI Provider System

E-014.1 defines portable, non-executing AI-provider SDK metadata. It owns the
exact `ai-provider-manifest.yaml` schema, provider identity and version,
SDK API level, unresolved Python entry point, transport and authentication
shapes, and host-recognized capabilities.

The reader is strict, deterministic, and secret-aware. It never imports provider
code, contacts a model service, resolves models, accesses credentials, or
executes a request. E-012 registers the plural `ups.ai-provider` manifest
family and delegates schema meaning to this subsystem.

E-014.2 adds deterministic exact-filename discovery below explicitly approved
roots, stable root provenance, duplicate identity rejection, SDK API-level
compatibility, and a catalog that resolves exact or highest versions with
optional host-recognized capability requirements. Multiple roots never imply
precedence; the same provider ID/version in two roots is an error.

Discovery, validation, and catalog resolution still never import an entry point,
contact a service, resolve models, or access credentials.

E-014.3 adds controlled project-local scaffolding. Provider-owned inputs are
validated here, then the built-in `provider.python-basic` definition is
executed through E-009 and E-008. Scaffolds are restricted to one direct child
of `Providers/` and contain the canonical manifest, a passive Python
entry-point class, and an author README.

E-014.4 adds immutable text request, response, usage, option, and structured
failure values plus the structural `RuntimeTextProvider` protocol. Its
host-owned registry binds only explicitly supplied instances whose identity,
version, SDK level, and declared `text-generation` capability match validated
metadata. Duplicate bindings are errors and registration never imports or
invokes the implementation.

E-014.5 adds controlled synchronous invocation over those explicit bindings.
The execution service resolves an exact or highest registered version, checks
that runtime identity has not drifted, invokes it exactly once, correlates the
result to the request, and contains exceptions or invalid results as safe
structured failures.

This subsystem does not define provider loading, streaming event payloads,
cancellation mechanics, retry policy, endpoint configuration, credential
resolution, model discovery, health checks, or application-container
integration.
