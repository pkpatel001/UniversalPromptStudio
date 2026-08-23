# ADR-0020: Controlled AI Provider Scaffold Generation

**Status:** Accepted  
**Milestone:** E-014.3

## Context

E-014.1 and E-014.2 established provider metadata, shared-manifest integration,
discovery, compatibility, and deterministic cataloging. The Engineering Toolkit
now needs provider generation without duplicating rendering, filesystem safety,
conflict handling, dry runs, or artifact tracking already owned by E-008 and
E-009.

The provider runtime execution contract is not yet complete. A scaffold must not
invent request, response, streaming, cancellation, retry, credential, endpoint,
or model-discovery behavior prematurely.

## Decision

### Composition boundary

`ProviderScaffoldService` validates provider-owned inputs and constructs the
canonical schema-1 `ProviderManifest`. It delegates generation to the built-in
E-009 template `provider.python-basic`.

E-009 owns the template definition, variables, artifacts, and
`.ups-artifact-manifest.json`. E-008 owns rendering, destination safety,
secret-context checks, conflict policy, dry runs, writes, and generation
reports. The provider subsystem does not write scaffold files directly.

### Generated artifacts

The template generates:

```text
ai-provider-manifest.yaml
provider.py
README.md
```

The Python file contains a passive entry-point class only. It does not implement
the existing placeholder backend interface or claim a finished provider runtime
contract. The README records the metadata, validation commands, and security
boundary.

After a successful real generation, the service parses the generated manifest
through the provider-owned reader and requires exact equality with the validated
request.

### Destination policy

Scaffolds are restricted to one direct child of the project-local
`Providers/` directory:

```text
Providers/<provider-directory>/
```

Absolute paths, traversal, deeper nesting, drive syntax, and destinations
outside `Providers/` are rejected. The default directory is derived
deterministically from the provider ID.

### Conflict and dry-run policy

Differing existing files are conflicts by default. Replacement requires an
explicit `--overwrite`. Dry runs execute planning and rendering but write no
provider directory or artifact manifest.

### CLI

```powershell
python -m Engineering generate provider PROVIDER_ID [OPTIONS]
```

Options include name, description, version, SDK level, transport,
authentication shape, repeatable capabilities, class name, destination, dry
run, and explicit overwrite.

## Security boundary

Generation does not import or instantiate provider code, contact a service,
access credentials, discover models, register a provider, make network
requests, or execute prompts. Authentication remains descriptive metadata only.

## Consequences

- Provider authors gain a consistent, validated starting structure.
- Provider scaffolding reuses the accepted E-009/E-008 pipeline rather than
  introducing ad-hoc writes.
- Generated artifacts remain traceable and verifiable.
- E-014.4 can define provider runtime request/response/failure contracts and
  controlled registration separately.
- Runtime loading, endpoints, credentials, model discovery, health checks,
  requests, streaming, retries, cancellation, and real provider integrations
  remain deferred.
