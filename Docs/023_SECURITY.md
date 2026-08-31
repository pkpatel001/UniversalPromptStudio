# Security

## Trusted plugin runtime

E-013.5 provides an explicit project-local Python plugin runtime. It is a
full-trust in-process design selected to finish the Engineering Toolkit quickly
while retaining a replaceable loader boundary.

Before code is imported, the host:

- validates plugin metadata, SDK compatibility, and dependencies;
- rejects symlinked, unsafe, ambiguous, excluded, or oversized directory
  content;
- captures one bounded immutable snapshot used for both SHA-256 approval and
  Python source loading;
- confirms the snapshot manifest equals the validated manifest;
- requires an exact ephemeral directory SHA-256 approval;
- requires an explicit full-trust acknowledgment; and
- blocks every plugin with a non-empty permission request.

Activation uses a manifest-capability-scoped registration context. Contributions
commit only after activation succeeds. Failure discards staged contributions and
removes the private module namespace. Deactivation clears host-owned
contributions and module state even when plugin cleanup fails. Loaded and
unloaded events are emitted only after successful lifecycle transitions.

This is not a security sandbox. Plugin code runs with the same process,
filesystem, network, environment, credential, and operating-system authority as
Universal Prompt Studio. A matching digest proves exact approved bytes only; it
does not authenticate a publisher, establish provenance, review code, or make
code safe. Do not activate code you do not fully trust.

There is no automatic startup loading, persisted approval, marketplace or remote
loading, package extraction or installation, permission enforcement, signature
verification, revocation, subprocess boundary, or OS sandbox.

## Deferred security areas

- process or OS isolation for untrusted plugins;
- enforceable plugin permissions;
- package signatures, publisher identity, provenance, and revocation;
- encryption;
- secret and credential storage; and
- future cloud-provider security.

## AI-provider metadata

E-014.1 provider manifests are portable metadata only. Their strict schema
rejects unknown and secret-like fields and has no endpoint, header, credential,
environment-variable, or machine-path fields. Authentication values describe a
future mechanism but never locate or grant a credential.

Provider inspection imports no code, performs no network request, and accesses
no credentials. Runtime provider authentication, secure credential resolution,
transport policy, TLS requirements, logging/redaction, and remote-service trust
remain deferred.

E-014.3 scaffold generation uses the controlled E-009/E-008 pipeline and writes
only below one direct child of `Providers/`. The generated entry point is
passive. Generation does not import code, contact a provider, access
credentials, or grant trust.

E-014.4 runtime registration accepts only an implementation instance explicitly
created and supplied by trusted host composition. It validates SDK
compatibility, exact manifest identity/version, and the declared
`text-generation` capability; duplicate identities never replace an existing
binding. Registration and resolution do not import entry points or invoke
provider methods. Request option names that appear to carry credentials are
rejected, but this is validation defense, not a credential-management system.

The runtime protocol is not a sandbox or an authorization grant. Loading code,
resolving credentials, contacting services, and enforcing timeouts, retries, or
cancellation remain outside E-014.4.

E-014.5 permits a trusted host to invoke an already-created, explicitly
registered provider instance. Before invocation, the host rechecks exact
identity/version. It calls the provider once, performs no automatic retry, and
requires a correlated typed result. Provider exceptions and malformed results
are replaced with bounded generic failures; raw exception text is not returned.

This execution boundary is not a sandbox. Invoked Python code retains the host
process's authority and could perform filesystem, environment, credential, or
network operations on its own. E-014.5 adds no provider loader, credential
resolver, endpoint configuration, authorization grant, or remote provider.
Only instances supplied by trusted host composition should be registered and
invoked.

E-014.6 wires only the host-authored `ups.offline-echo` implementation into the
application composition root. It uses local deterministic string operations
and does not read files, inspect the environment, resolve credentials, or make
network requests. The adapter rejects credential-like request option names and
translates SDK failures without exposing contained provider exceptions.

This reference integration does not make arbitrary provider manifests
executable. There is still no entry-point loader, trust store, endpoint or
credential configuration, remote provider, automatic retry, or runtime
sandbox. The generic execution API must continue to receive only instances
explicitly created by trusted host composition.

## Theme metadata

E-015.1 theme manifests are declarative metadata only. Their exact schema
accepts identity, version, SDK level, appearance categories, and a fixed set of
opaque hexadecimal semantic colors. Unknown and secret-like fields are
rejected.

Schema 1 contains no CSS, scripts, URLs, asset paths, fonts, icons, commands,
credentials, or machine-local values. Theme inspection loads no assets, injects
no styles, modifies no frontend files, executes no code, and grants no trust.

The metadata reader is not a CSS sanitizer or accessibility certification
system. Asset handling, CSS emission, frontend application, live preview,
contrast enforcement, installation, and untrusted-theme policy remain deferred.

E-015.2 discovery scans only explicitly approved roots for the exact theme
manifest filename. It does not follow symlinked roots, directories, or
manifests, and ignores dependency, cache, VCS, build, distribution, and Rust
target directories. Root provenance is retained and duplicate theme
ID/version pairs fail instead of creating implicit precedence.

SDK compatibility and appearance matching are metadata classifications only.
They do not load palette values into the UI, validate contrast, establish
publisher trust, or make a theme safe to install or apply.

E-015.3 scaffold generation uses the controlled E-009/E-008 pipeline and writes
only below one direct child of `Themes/`. It generates a strict declarative
manifest, an author README, and the E-009 artifact manifest. Dry runs write
nothing, replacement requires explicit overwrite, and a successful real write
is re-read through the theme-owned parser for exact equality.

Generated themes contain no CSS, scripts, URLs, assets, fonts, icons, commands,
or credentials. Generation does not modify frontend files, install or select a
theme, evaluate contrast, apply styles, or grant trust.

E-015.4 token compilation accepts only a validated `ThemeManifest` and one
recognized appearance. It maps the closed schema-1 color roles to exactly eleven
fixed `--ups-color-*` names. Values remain the opaque hexadecimal colors already
validated by the manifest reader. Missing palettes fail; there is no appearance
fallback.

The serializer emits declarations only, without selectors, braces, URLs, file
references, arbitrary properties, or writes. It does not inject CSS, modify the
DOM or frontend, install or select a theme, evaluate contrast, apply styles, or
grant trust. Selector ownership and runtime application remain a separate trust
and integration boundary.

E-015.5 implements that application boundary for host-authored frontend
selections only. The controller requires exact identity, version, appearance,
and token keys; rejects missing, unknown, malformed, or non-hexadecimal data
before mutation; and maps values only to the eleven fixed `--ups-color-*`
properties. It never accepts selectors, property names, stylesheet text, HTML,
URLs, paths, scripts, or commands from the payload.

Application snapshots current property values, priorities, and bounded
`data-ups-*` attributes. Failed replacement rolls back to the previous snapshot,
while explicit revert restores the original pre-theme baseline. The UI performs
If revert fails, the complete active snapshot is restored. The UI performs no
automatic activation, persistence, file access, network access, Tauri command,
or capability expansion.

The E-015.5 built-in selections are trusted host code, not installed theme
packages. E-015.6 replaces their duplicated source and adds bounded opt-in
preferences below; external installation, provenance, untrusted-theme handling,
and accessibility certification remain deferred.

E-015.6 replaces duplicated frontend presets with a deterministic generated
catalog compiled from compatible manifests below explicitly approved roots. The
synchronizer writes only the fixed frontend module, rejects symlinked path
components and oversized existing output, and uses atomic replacement. Check
mode writes nothing, and desktop packaging rejects stale generated data.

Generated selections contain only validated identity, bounded display name,
recognized appearance, and the eleven fixed color tokens. The frontend validates
the entire generated module again before lookup. Transport adds no YAML parser,
filesystem API, Tauri command, permission, capability, or network request to the
runtime application.

Preference persistence is explicit and browser-local. It stores only schema
version, theme ID, theme version, and appearance in a bounded exact-shape record.
It never stores tokens, CSS, paths, assets, or manifest content. Startup restore
requires an exact match in the current validated catalog; invalid, stale,
oversized, unknown, or inaccessible records are not applied. Opt-out, Default,
and Revert clear the record.

This does not authenticate or install external themes, establish publisher
provenance, migrate preferences, certify accessibility, or make untrusted
content safe. Those boundaries remain deferred.

E-015.7 adds a project-local external-theme ingress boundary. A canonical ZIP
contains exactly one root declarative manifest; bounded inspection uses one byte
snapshot, validates the strict schema without extraction, and hashes both the
archive and manifest. Extra members, symlinked packages or members, encryption,
unsupported compression, oversized content, malformed UTF-8/YAML, and identity
mismatches are rejected.

Installation requires an exact caller-supplied SHA-256 and a separate explicit
external-theme acknowledgement. The host derives
`Themes/Installed/<id>/<version>`, rejects symlinked components, compatibility or
discovery failures, duplicates, and existing targets, and atomically moves a
private staging directory into place. The installed manifest is the exact
inspected content. A deterministic receipt records the caller's bounded source
label, file identity, content hashes and sizes, and approval policy.

Hash approval proves byte equality only. The source label is caller-provided
provenance, not authenticated publisher identity. No signature, certificate,
reputation, persistent trust grant, network acquisition, update, replacement,
removal, or revocation mechanism is added. Installation does not transport the
theme to the frontend or activate it; those remain separate explicit boundaries.

E-015.8 makes E-015.7 provenance an admission requirement for managed themes.
The exact bounded JSON receipt rejects duplicate or unknown keys and validates
identity, version, canonical package filename, digests, size, trust policy, and
acknowledgement. Discovery accepts a manifest beneath `Themes/Installed/` only
when its directory contains exactly the regular manifest and receipt files, its
current bytes match the recorded size and SHA-256, and manifest, receipt, and
directory identities agree. Failures are excluded and block catalog compilation.

Disable and restore require the exact recorded package digest, a separate action
acknowledgement, a verified unchanged source, and an absent target. The operation
is an atomic same-volume move between `Installed/` and the ignored
`.ups-theme-disabled/` holding area. It never merges, overwrites, rewrites, or
deletes installed evidence and does not synchronize or apply frontend themes.

The receipt is unsigned local evidence. Verification detects inconsistent or
accidentally modified state, but it cannot authenticate a publisher or resist a
malicious local writer able to replace both manifest and receipt. Signatures,
certificates, remote revocation, secure deletion, network acquisition, and
automatic repair remain outside this boundary.

## Workflow metadata

E-016.1 workflow manifests are passive declarative graph definitions. Their
exact bounded schema accepts identity, typed ports, host-recognized operation
IDs, and explicit data-flow edges. Unknown fields, secret-like keys, and
high-confidence secret-bearing values are rejected.

Schema 1 contains no embedded code, expressions, import paths, entry points,
commands, environment lookups, credentials, default values, node
configuration, filesystem paths, or URLs. Inspection imports no operation,
registers no handler, executes no node, contacts no service, launches no
subprocess, reads no credential, and writes no file.

Operation IDs are descriptive host vocabulary only; they do not authorize or
locate an implementation. SDK compatibility, discovery, catalog construction,
planning, registration, execution, persistence, retries, scheduling, and
plugin- or provider-supplied operations remain separate future trust
boundaries.

E-016.2 discovery accepts only explicit labeled roots and the exact workflow
manifest filename. It rejects symlinked roots and manifests, does not follow
symlinked directories, and ignores dependency, cache, VCS, build, distribution,
and Rust target directories. Depth, manifest count, and individual file size
are capped. Duplicate identity/version pairs fail rather than invoking implicit
root precedence.

Compatibility and catalog resolution inspect metadata only. They do not import
operation modules, register handlers, infer permissions, plan execution, or run
nodes. Catalog filtering by operation ID confirms only that a manifest declares
the identifier; it does not prove an implementation exists or is trusted.

Every workflow input must be used, every node must contribute to an output, and
all graph references, target bindings, types, and cycles remain validated before
catalog admission. These checks establish structural coherence, not runtime
safety or authorization.

### Controlled workflow scaffold generation

E-016.3 accepts bounded workflow metadata and one host-vocabulary operation ID,
constructs the full typed graph, and passes its exact serialized form through
the producer-owned manifest reader before any generation write. Secret-like
manifest values, malformed identities, invalid graph state, and destinations
outside one direct child of 'Workflows/' therefore fail before files are
created.

The domain service delegates template resolution and artifact evidence to
E-009 and rendering, path safety, dry-run, conflict policy, rollback, and writes
to E-008. Successful non-dry-run output is reread through WorkflowSystem and
must be semantically identical to the prevalidated request.

The built-in template emits only the canonical declarative manifest and README;
E-009 adds its deterministic integrity manifest. It emits no Python or
JavaScript, import or module path, expression, command, credential lookup,
endpoint, URL, handler, or runtime configuration. Generation does not imply
that the referenced operation exists or is trusted, and does not plan,
register, or execute it.

### Workflow handler registration and planning

E-016.4 permits only trusted host code to supply already-created handler
objects. Workflow manifests still contain operation IDs only; they cannot name
modules, entry points, commands, constructors, endpoints, or credentials.
Registration snapshots the handler's identity, Workflow SDK level, and complete
ordered port contracts, rejects duplicate IDs, and never invokes the handler.

Planning revalidates graph coherence and workflow SDK compatibility, then
requires an exact registered operation, SDK level, and port contract for every
node. Missing and mismatched bindings become deterministic structured failures.
Topological ordering uses a lexical node-ID tie break and does not infer
precedence from manifest or registry insertion order.

The handler protocol exposes an execution method solely to the controlled
E-016.5 runner. Registration and planning never call it and perform no dynamic
import, discovery, instantiation, network access, credential access, subprocess,
filesystem write, event emission, persistence, retry, or scheduling.

### Controlled workflow execution

E-016.5 freezes caller values into immutable JSON-shaped transport before
invocation. Strings, collection sizes, object keys, nesting depth, named ports,
and aggregate value nodes are bounded; floats must be finite and null or
arbitrary Python objects are rejected. Port names and value types must exactly
match the validated plan.

Immediately before each call, the runner rechecks the handler's operation ID,
SDK level, and ordered port contracts against its registration snapshot. Each
handler is invoked at most once. The first drift, exception, invalid output,
aggregate overflow, or event-delivery failure stops the run. There is no retry
or continuation. Only validated completed-step results survive in a failure;
failed raw output and exception details are discarded.

Lifecycle events carry run/workflow identity, version, completed-step count,
success state, and a stable failure code only. They never carry runtime inputs,
outputs, or exception messages. Input validation occurs before the started
event. Failed started-event delivery prevents handler invocation.

The two reference handlers and reference graph are host-authored, deterministic,
and offline. The application container creates and registers them explicitly
and bridges lifecycle metadata to the existing Backend workflow events. The
legacy placeholder engine remains unchanged.

Execution is not a sandbox. Trusted handlers execute in-process with host
authority and may perform effects the runner cannot prevent. E-016 adds no
dynamic handler loading, plugin operations, network acquisition, credentials,
parallelism, retry policy, cancellation, persistence, resume, scheduling, or
remote triggers. Those require separate future trust and product decisions.

## Controlled Engineering self-generation planning

E-017.1 defines self-generation as a human-requested allowlisted plan, not
autonomous repository modification. The request accepts only bounded
package/module identifiers, descriptive text, and an optional CLI-placeholder
flag. It accepts no repository destination, relative path, template identifier,
import path, command, overwrite permission, credential, URL, or executable
content.

Every planned path is derived from a fixed host-owned inventory beneath
'Engineering/'. Readiness requires exact regular, non-symlinked evidence for
E-007 through E-016, a recognized project root, no symlinked destination
component, and no existing destination. Reports are immutable, deterministic,
and explicitly state that no files were written.

The planner does not import milestone implementations, resolve or execute
templates, render content, read credentials or environment variables, access
the network, launch subprocesses, invoke commands, mutate Git, create
directories, or write files. Renderer keys are inert host vocabulary reserved
for E-017.2.

This boundary is not a Python sandbox. Trusted code could bypass the planner or
replace in-process constants. The host must expose the typed planner to request
sources, keep execution behind the later controlled E-009/E-008 service, and
require human review of every generated diff. Automatic approval, commits,
pushes, releases, publishing, dependency installation, arbitrary paths or
templates, and replacement of security-sensitive core logic remain forbidden.


## Controlled Engineering self-generation execution

E-017.2 executes only the current unchanged E-017.1 ready plan. Callers still
cannot provide paths, template IDs, import paths, commands, credentials, or
overwrite authority. Two fixed host definitions map the allowlisted subsystem
with or without its optional passive CLI adapter.

E-009 artifact paths may interpolate only simple declared string fields.
Attribute or index lookup, conversions, format specifications, missing fields,
and non-string fields fail. E-008 validates every expanded destination against
the project root before writing. Two in-memory previews must be byte-identical
and match the accepted artifact path, type, and renderer-key plan exactly.

Execution always uses no-overwrite behavior. Artifacts are written by E-008 and
recorded with the E-009 SHA-256 manifest. Any later write, manifest, structural,
isolated-import, or reproducibility failure removes the new exact files and
newly created empty directories. Rollback never authorizes replacement of an
existing destination.

Check mode writes nothing. It compares current files both to manifest hashes
and freshly rendered approved template bytes, then repeats UTF-8 Python parsing,
compilation, and isolated package import. Import verification disables bytecode
writes and removes its private module namespace, but it executes trusted
host-authored generated Python in-process and is not a sandbox.

E-017.2 adds no Git operation, automatic approval, release, publishing,
dependency installation, network request, credential lookup, subprocess,
arbitrary command, arbitrary template, or security-sensitive core replacement.
Every generated diff still requires human review.

## Bounded desktop-to-Python IPC

A-002.1 exposes five Tauri commands: readiness, project list/create, and
project-scoped prompt list/create. Each accepts only bounded command-specific
values. The webview cannot select an executable, database path, environment
value, Python module, function, sidecar command, arbitrary payload, or SQL.

Both development and release hosts launch only the target-triple sidecar declared
by Tauri `externalBin`. The webview retains only `core:default`; no shell-plugin
or filesystem permission is exposed. Rust clears the child environment,
restores only the three variables required by the Windows frozen runtime, and
adds the trusted `UPS_APP_DATA_DIR` value resolved through Tauri. Python appends
only the fixed `prompt-library.sqlite3` filename.

The JSON-lines protocol rejects unknown or duplicate fields, malformed UTF-8 or
JSON, unsupported versions, non-finite values, malformed identifiers, unknown
payload fields, messages over 16 KiB, uncorrelated responses, and responses
outside the three-second timeout. Rust revalidates entity shapes, UUIDs,
timestamps, text and collection bounds, and project ownership. Transport failure
discards the child so a later action may start a fresh process.

SQLite schema version 1 is application-owned through `PRAGMA user_version`.
Startup checks database integrity, required schema shape, and foreign-key
relationships. Foreign keys are enabled on every connection. Future, corrupt,
unmanaged, incomplete, relationship-invalid, or unavailable databases fail with
bounded errors and are never deleted, replaced, renamed, truncated, downgraded,
or automatically repaired.

The router performs no prompt execution, provider request, workflow execution,
credential access, network operation, arbitrary file access, or subprocess
launch. Python error detail never crosses Rust; unknown failures collapse to a
fixed unavailable response. Source, frozen, restart, and installed-layout tests
verify records remain under per-user app data rather than the installation.

The Python process remains trusted code with normal process authority. IPC
validation reduces the webview's authority but is not a sandbox or process
isolation boundary.
