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
