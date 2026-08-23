# Universal Prompt Studio AI Provider SDK

## Scope through E-014.6

E-014.1 establishes portable provider identity and capability metadata.
E-014.2 adds deterministic multi-root discovery, SDK compatibility
classification, and catalog resolution. E-014.3 adds controlled provider
scaffold generation through E-009 and E-008. E-014.4 adds typed text-runtime
values and controlled registration of host-supplied instances. E-014.5 adds
controlled synchronous invocation of those explicit registrations. E-014.6
adds an offline reference provider and Backend infrastructure adapter. Reading,
discovering, validating, resolving, generating, or registering provider
metadata never imports its entry point, accesses credentials, performs network
requests, discovers models, or executes prompts.

The existing `Backend.interfaces.AIProvider` remains the phase-one synchronous
application interface. E-014.6 connects it through an infrastructure adapter
without changing the application service contract. Streaming, cancellation
mechanics, retries, embeddings, multimodal payloads, runtime configuration, and
loading require later checkpoints.

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
python -m Engineering generate provider example.echo-ai --capability text-generation --dry-run
python -m Engineering generate provider example.echo-ai --capability text-generation
python -m Engineering manifest types
python -m Engineering manifest inspect
python -m Engineering manifest validate
```

`provider inspect` preserves E-014.1 exact-file inspection. Catalog commands
require at least one explicit root and remain read-only and non-executing.
Provider loading, runtime configuration, credential resolution, and request
execution are not implemented by this checkpoint.

## Controlled scaffold generation

The built-in `provider.python-basic` template generates exactly:

```text
Providers/<provider-directory>/
├── ai-provider-manifest.yaml
├── provider.py
├── README.md
└── .ups-artifact-manifest.json
```

The artifact manifest is owned by E-009. Rendering, portable destination
validation, conflict handling, dry runs, secret-context checks, and controlled
writes are owned by E-008.

The destination must be one direct child of `Providers/`. Existing differing
files are preserved unless `--overwrite` is explicit. The generated Python
class remains passive: E-014.4 defines the text request, response, failure, and
registration boundary, but scaffold generation does not opt generated code into
that protocol or establish a loading and execution path.

## Typed text runtime boundary

The E-014.4 public API includes:

- `ProviderTextRequest` with request identity, prompt, optional model, and an
  immutable tuple of portable scalar options;
- `ProviderTextResponse` with correlated request identity, text, optional
  model, and non-negative usage values;
- `ProviderFailure` and `ProviderFailureCode` for stable failure reporting;
- the structural `RuntimeTextProvider` protocol; and
- `ProviderRuntimeRegistry` for explicit metadata-to-instance binding.

Request option names are stable lowercase identifiers, must be unique, and
reject credential-like names. Values are strings, integers, finite floats, or
booleans. These options are request data, not runtime configuration or a place
to store credentials.

The registry validates the manifest SDK level, requires the declared
`text-generation` capability, checks exact provider ID/version equality, and
rejects duplicates. It can resolve an exact version or the highest registered
version and can explicitly unregister one binding. It never imports the
manifest entry point and never calls `generate_text`.

Structured timeout, rate-limit, and cancellation outcomes are classifications
only; timeout, retry, and cancellation mechanisms remain deferred with provider
loading, credentials, endpoints, model discovery, health checks, and real
integrations.

## Controlled invocation

`ProviderExecutionService` accepts a host-owned `ProviderRuntimeRegistry`. Its
`execute` operation resolves an exact or highest registered version and checks
the implementation identity/version again before calling `generate_text`
exactly once.

The immutable `ProviderExecutionReport` identifies the resolved provider and
version and contains either a response or failure. Its `succeeded` property is
true only for `ProviderTextResponse`.

The host preserves valid correlated provider results. It converts these cases
to a non-retryable `provider-error`:

- the implementation identity changes after registration;
- provider code raises an exception;
- provider code returns a value outside the result contract; or
- the returned request ID does not match the request.

Exception text is not copied into the failure. Unknown registrations and
invalid host request arguments remain `ProviderError` selection/contract
errors because no provider was successfully invoked.

This service does not load provider code, instantiate entry points, configure
models or endpoints, resolve credentials, retry, cancel, stream, or connect the
Backend application flow by itself. It invokes trusted host-supplied Python code
and is not a sandbox; that code retains the host process's authority.

## Offline application integration

`OfflineEchoProvider` is a built-in, deterministic implementation with identity
`ups.offline-echo` version `1.0.0`. Its host-owned metadata declares local
transport, no authentication, and `text-generation`. It returns a predictable
response and character-count usage without filesystem, environment, credential,
or network access.

`ProviderRuntimeAIAdapter` lives in the Backend infrastructure layer and
implements the existing `AIProvider` ABC. It translates application parameters
to immutable SDK options, treating `model` specially and converting underscores
to hyphens. Credential-like option names and normalized duplicate names remain
errors.

On success, the adapter returns the existing `PromptExecutionResult` with
provider identity, version, correlated request ID, usage, and optional model in
metadata. A structured SDK failure becomes `AIProviderExecutionError`, which
retains the safe message, stable code, provider name, and retryability.

The application composition root registers `ups.offline-echo` alongside the
legacy `dummy` implementation and exposes the host-owned runtime registry. No
manifest is imported or dynamically loaded. This is a reference integration,
not remote-provider support or a generic trust policy.
