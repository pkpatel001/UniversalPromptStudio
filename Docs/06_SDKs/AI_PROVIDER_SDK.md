# Universal Prompt Studio AI Provider SDK

## E-014.1 scope

E-014.1 establishes portable provider identity and capability metadata before
provider generation or runtime integration. Reading or validating a provider
manifest never imports its entry point, accesses credentials, performs network
requests, discovers models, or executes prompts.

The existing `Backend.interfaces.AIProvider` remains the phase-one synchronous
application interface. It is not yet the completed AI Provider SDK execution
contract. Streaming, cancellation, structured errors, retries, embeddings,
multimodal payloads, and runtime configuration require later checkpoints.

## Manifest schema 1

Each provider implementation uses the exact filename
`ai-provider-manifest.yaml`:

```yaml
schema_version: 1
provider:
  id: example.echo-ai
  name: Echo AI
  version: 1.0.0
  sdk_version: 1
  description: Provides deterministic local text generation.
  entry_point: echo_provider:EchoProvider
  transport: local
  authentication: none
  capabilities:
    - streaming
    - text-generation
```

All fields are required. Unknown fields and duplicate capabilities are rejected.
The manifest must declare at least one host-recognized capability.

Portable manifests do not contain endpoint URLs, headers, environment-variable
names, model inventories, credential names or values, retry policy, timeouts, or
machine-local paths. Those values change by installation and belong to future
runtime configuration.

## Identity and versions

Provider IDs are stable lowercase vendor-qualified identifiers, such as
`openai.api` or `local.ollama`. Provider implementation versions use
canonical PEP 440 with exactly three release components. `sdk_version` is a
positive integer API level and is independent of both manifest schema and
implementation version.

The current metadata API level is 1. Compatibility classification and catalog
resolution are deferred to E-014.2.

## Capabilities

Schema 1 recognizes:

- `text-generation`
- `streaming`
- `embeddings`
- `vision`
- `image-generation`
- `audio-input`
- `audio-output`
- `tool-calling`

Capabilities state what a provider implementation intends to support. They do
not prove runtime compatibility, model availability, authorization, or service
readiness.

## Transport and authentication

`transport` is either `local` or `http`. It describes the future runtime
shape only and is not an endpoint.

`authentication` is one of `none`, `api-key`, `oauth2`, or `external`.
It declares an authentication category only. It never names, locates, reads, or
grants access to a credential.

## Entry point

`entry_point` uses `module.path:ClassName` syntax. E-014.1 validates the
string but does not resolve the module or class. Manifest validity is not a
trust decision and does not make provider code safe to execute.

## Shared manifest family

E-012 registers provider manifests as:

```text
stable id:       ups.ai-provider
kind:            ai-provider
filename:        ai-provider-manifest.yaml
current schema:  1
readable schema: 1
cardinality:     many
```

## Commands

```powershell
python -m Engineering provider inspect C:\path\to\ai-provider-manifest.yaml
python -m Engineering manifest types
python -m Engineering manifest inspect
python -m Engineering manifest validate
```

`provider inspect` is read-only and non-executing. Provider discovery,
cataloging, generation, loading, runtime configuration, and request execution
are not implemented by this checkpoint.
