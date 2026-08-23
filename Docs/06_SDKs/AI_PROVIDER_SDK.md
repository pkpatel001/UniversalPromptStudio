# Universal Prompt Studio AI Provider SDK

## Scope through E-014.2

E-014.1 establishes portable provider identity and capability metadata.
E-014.2 adds deterministic multi-root discovery, SDK compatibility
classification, and catalog resolution. Reading, discovering, validating, or
resolving provider metadata never imports its entry point, accesses credentials,
performs network requests, discovers models, or executes prompts.

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

The current metadata API level is 1. The default host supports exactly level 1.
Structurally valid future levels remain inspectable but are classified as
`too-new`; older unsupported levels are `too-old`. Compatibility does not
establish trust or runtime readiness.

## Discovery and provenance

Provider discovery is recursive, sorted, exact-filename, and read-only below
one or more explicitly approved `--root` paths. Each root receives a stable
label retained by records and issues. VCS, cache, virtual-environment,
dependency, build, distribution, and Rust target directories are ignored.
Symlinked roots, directories, and manifests are not followed.

Root IDs and resolved root paths must be unique. Duplicate provider ID/version
pairs across or within roots are errors. Roots have no implicit precedence, and
one source never silently replaces another.

## Catalog resolution

The in-memory catalog contains SDK-compatible metadata only. It provides:

- stable provider and version ordering;
- exact-version resolution;
- highest-version resolution when no version is supplied;
- filtering by one or more required capabilities; and
- stable version inventory for a provider ID.

Capability matching is set inclusion over manifest declarations. It does not
probe a service or claim that a particular model supports the behavior.

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
python -m Engineering provider list --root C:\path\to\providers
python -m Engineering provider validate --root C:\project\providers --root C:\approved\providers
python -m Engineering provider resolve example.echo-ai --root C:\path\to\providers
python -m Engineering provider resolve example.echo-ai --root C:\path\to\providers --capability streaming
python -m Engineering manifest types
python -m Engineering manifest inspect
python -m Engineering manifest validate
```

`provider inspect` preserves E-014.1 exact-file inspection. Catalog commands
require at least one explicit root and remain read-only and non-executing.
Provider generation, loading, runtime configuration, credential resolution, and
request execution are not implemented by this checkpoint.
