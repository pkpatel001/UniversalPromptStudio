# AI Provider System

E-014.1 defines portable, non-executing AI-provider SDK metadata. It owns the
exact `ai-provider-manifest.yaml` schema, provider identity and version,
SDK API level, unresolved Python entry point, transport and authentication
shapes, and host-recognized capabilities.

The reader is strict, deterministic, and secret-aware. It never imports provider
code, contacts a model service, resolves models, accesses credentials, or
executes a request. E-012 registers the plural `ups.ai-provider` manifest
family and delegates schema meaning to this subsystem.

This checkpoint does not define runtime execution, streaming event payloads,
cancellation, retry policy, endpoint configuration, credential resolution,
model discovery, provider loading, scaffolding, or application-container
integration.
