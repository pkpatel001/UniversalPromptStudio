# AI Provider Development

## Current checkpoint

Through E-014.3, the toolkit supports strict manifest authoring, explicit-root
discovery, SDK compatibility validation, deterministic catalog resolution, and
controlled project-local scaffold generation. Begin with
`AI_PROVIDER_SDK.md`, ADR-0018, ADR-0019, and ADR-0020. Do not place runtime
configuration or credentials in a provider manifest.

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
import it or establish the later runtime execution contract.

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

Runtime loading, configuration, credentials, requests, streaming, retries,
cancellation, health checks, and model discovery remain later E-014 work.
