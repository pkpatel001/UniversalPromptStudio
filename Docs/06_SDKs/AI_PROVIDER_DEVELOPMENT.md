# AI Provider Development

## Current checkpoint

E-014.1 supports strict manifest authoring and inspection only. Begin with
`AI_PROVIDER_SDK.md` and ADR-0018. Do not place runtime configuration or
credentials in a provider manifest.

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

## Security boundary

Manifest inspection does not import the entry point, call a provider, access the
network, inspect environment variables, or read credentials. Authentication is
descriptive metadata only.

Provider code generation, SDK compatibility, provider discovery/cataloging,
runtime loading, configuration, credentials, requests, streaming, retries, and
cancellation remain later E-014 work.
