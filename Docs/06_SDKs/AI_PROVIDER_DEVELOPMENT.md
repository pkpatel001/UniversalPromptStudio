# AI Provider Development

## Current checkpoint

Through E-014.5, the toolkit supports strict manifest authoring, explicit-root
discovery, SDK compatibility validation, deterministic catalog resolution, and
controlled project-local scaffold generation. It also defines immutable text
request/response/failure contracts and explicit host-owned runtime
registration plus controlled invocation. Begin with `AI_PROVIDER_SDK.md`,
ADR-0018 through ADR-0022. Do
not place runtime configuration or credentials in a provider manifest.

## Generate a scaffold

Preview without writing:

```powershell
python -m Engineering generate provider example.echo-ai --capability text-generation --dry-run
```

Generate the scaffold:

```powershell
python -m Engineering generate provider example.echo-ai --name "Echo AI Provider" --capability text-generation
```

The default destination is `Providers/example-echo-ai`. A custom
`--destination` must still be one direct child of `Providers/`. Use
repeatable `--capability` options and select only recognized transport and
authentication metadata. Existing differing files are conflicts unless
`--overwrite` is explicit.

The generated `provider.py` is intentionally passive. Generation does not
import it or automatically opt it into runtime registration.

## Implement the text runtime protocol

`RuntimeTextProvider` exposes exact typed `provider_id` and `version`
properties plus `generate_text(ProviderTextRequest)`. A result is either
`ProviderTextResponse` or `ProviderFailure`; provider-specific exceptions must
not become part of the portable SDK contract. Request options are immutable,
scalar, uniquely named, and reject credential-like names.

`ProviderRuntimeRegistry.register(record, implementation)` is controlled by
the host. It accepts only SDK-compatible records that declare
`text-generation`, requires the implementation identity and version to match,
and rejects duplicates. The registry receives an already-created instance: it
does not resolve the manifest entry point, import a module, or call
`generate_text`. Registration therefore does not establish trust or service
readiness.

## Invoke an explicitly registered provider

Construct `ProviderExecutionService` with a host-owned runtime registry, then
call `execute(provider_id, request, version)` only after the host has explicitly
registered the intended instance. Omitting `version` selects the highest
registered version; supplying it selects that exact version.

The service checks runtime identity again immediately before invocation and
calls `generate_text` exactly once. A valid response or structured failure is
preserved. Exceptions, invalid return types, and mismatched request IDs become
a non-retryable `provider-error` with a bounded host message. Provider exception
text is not exposed.

## Author and inspect metadata

Create `ai-provider-manifest.yaml` beside the future provider implementation,
using all required schema-1 fields. Then inspect it without executing code:

```powershell
python -m Engineering provider inspect .\ai-provider-manifest.yaml
```

The shared manifest catalog can inventory multiple provider documents:

```powershell
python -m Engineering manifest validate --root C:\path\to\project
```

Validate provider compatibility and resolve a provider without importing it:

```powershell
python -m Engineering provider validate --root C:\path\to\providers
python -m Engineering provider list --root C:\path\to\providers
python -m Engineering provider resolve example.echo-ai --root C:\path\to\providers --capability text-generation
```

Repeat `--root` only for directories you explicitly approve. Duplicate
provider ID/version pairs across roots are errors; root order is not a
replacement or trust policy.

## Security boundary

Manifest inspection does not import the entry point, call a provider, access the
network, inspect environment variables, or read credentials. Authentication is
descriptive metadata only.

Provider loading, configuration, credentials, streaming, retries, cancellation
mechanics, health checks, model discovery, Backend application integration, and
real provider integrations remain later E-014 work. A structured failure code
names a portable outcome category; it does not implement timeout, retry, or
cancellation policy.
