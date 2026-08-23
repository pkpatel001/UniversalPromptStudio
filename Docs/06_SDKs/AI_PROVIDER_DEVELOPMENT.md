# AI Provider Development

## Current checkpoint

Through E-014.2, the toolkit supports strict manifest authoring, explicit-root
discovery, SDK compatibility validation, and deterministic catalog resolution.
Begin with `AI_PROVIDER_SDK.md`, ADR-0018, and ADR-0019. Do not place runtime
configuration or credentials in a provider manifest.

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

Provider code generation, runtime loading, configuration, credentials, requests,
streaming, retries, cancellation, health checks, and model discovery remain
later E-014 work.
