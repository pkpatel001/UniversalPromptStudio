# Universal Prompt Studio Plugin SDK

## Scope

Through E-013.5 the Plugin SDK can describe,
validate, discover, compatibility-check, dependency-check, and catalog plugins
and generate a controlled project-local scaffold. It can inspect a bounded
package, produce a non-mutating installation plan, and explicitly activate an
exact approved project-local source snapshot through the trusted runtime. A
valid manifest, package, or digest is not a publisher identity or code-safety
claim.

Permission enforcement, archive creation or extraction, installation, trust
persistence, signature verification, process or OS isolation, remote
repositories, marketplaces, automatic startup loading, and UI management are
not implemented.

## Trusted runtime lifecycle

The E-013.5 runtime is deliberately explicit and project-local:

1. `plugin runtime digest` validates the selected plugin and captures a
   bounded immutable directory snapshot without importing code.
2. The caller independently reviews the code and supplies the exact snapshot
   SHA-256 plus `--acknowledge-full-trust`.
3. The host re-captures the directory, verifies the digest and manifest, loads
   source bytes under a private namespace, instantiates the declared class, and
   calls `activate(context)`.
4. Staged contributions commit only after activation returns successfully.
5. Explicit deactivation calls `deactivate(context)`, clears host-owned
   contributions, and removes every loader-owned module.

The default `TrustedInProcessLoader` sits behind `PluginModuleLoader`, so a
future process-isolated implementation can replace it without changing the
lifecycle manager. The current loader does not modify persistent `sys.path`
state and executes Python source from the approved snapshot bytes. Dotted entry
points and relative plugin imports use the same private snapshot namespace.

The runtime is not a sandbox. Plugin code has the host process's full Python and
operating-system authority. Permission requests cannot be enforced, so any
non-empty manifest `permissions` list blocks runtime digest approval and
activation. Trust and lifecycle state are in memory only; nothing loads
automatically on startup.

The entry-point class structurally implements:

```python
class ExamplePlugin:
    def activate(self, context: PluginRegistrationContext) -> None:
        context.register("commands", "example.echo", object())

    def deactivate(self, context: PluginRegistrationContext) -> None:
        pass
```

Registration accepts only manifest-declared capability IDs and unique
contribution IDs. Activation failures roll back all staged contributions and
module state. Deactivation failures still clear host-owned contributions and
module state, but the lifecycle ends in `failed`.

## Package and trust planning

The canonical package filename is
`<plugin-id>-<plugin-version>.ups-plugin.zip`. Its root contains
`plugin-manifest.yaml` and the declared entry-point module. Inspection is
read-only: every regular file is bounded and hashed, unsafe or ambiguous paths
are rejected, and no member is extracted.

Installation planning targets `<root>/<plugin-id>/<plugin-version>/` below one
explicitly approved existing root. Readiness requires an exact SHA-256 value
supplied for that invocation. This ephemeral hash approval is an integrity
check only; it is not a signature, publisher identity, persistent trust record,
code review, permission grant, or claim that execution is safe.

## Plugin identity

Every plugin has a vendor-qualified ID such as `example.echo`.

- IDs contain at least two lowercase dot-separated segments.
- A segment starts with a letter and may contain digits and internal hyphens.
- IDs are stable and case-sensitive.
- The complete ID is at most 128 characters.

Plugin versions use a restricted canonical PEP 440 form with exactly
`major.minor.patch` release components and no epoch or local version.
Canonical pre-release, post-release, and development segments are supported.
The catalog rejects duplicate ID/version pairs. An exact version can be
requested; otherwise the highest registered version is returned.

## SDK compatibility

`sdk_version` is a positive integer API level. The manifest reader accepts
future positive levels so inspection can explain their metadata. The current
host compatibility contract supports SDK API level 1. It is deliberately
separate from:

- `schema_version`, which versions the YAML structure; and
- `plugin.version`, which versions the plugin itself.

## Manifest schema 1

Each plugin uses the exact filename `plugin-manifest.yaml`.

```yaml
schema_version: 1
plugin:
  id: example.echo
  name: Echo Plugin
  version: 1.0.0
  sdk_version: 1
  description: Adds echo-oriented contributions.
  entry_point: example_echo.plugin:EchoPlugin
  capabilities:
    - commands
    - views
  permissions:
    - network.read
  dependencies:
    - id: example.base
      version: ">=1,<2"
```

All shown keys are required, including empty lists. Unknown keys are rejected.
The root and `plugin` values must be mappings. Scalar and collection types are
strict; booleans do not satisfy integer fields.

Schema 1 intentionally has no arbitrary command, resource-path, credential,
secret, or machine-state fields.

## Entry point

The entry point must use `module.path:ClassName` syntax. Validation checks only
the string grammar. Inspection does not:

- import the module;
- resolve the class;
- instantiate the class;
- call activation logic; or
- execute plugin code.

`Engineering.PluginSystem.RuntimePlugin` is the structural runtime contract.
`Backend.interfaces.Plugin` is retained as a compatible abstract base class
for application code and now includes both lifecycle methods.

## Capabilities

Capabilities are lowercase metadata identifiers, for example `commands`,
`views`, or `workflow.nodes`. They describe intended contribution categories
only. Values are unique and normalized into stable ordering.

## Permission requests

Permissions use the same bounded identifier syntax, for example
`network.read`. They are declarations only:

- validation does not grant a permission;
- discovery does not enforce a permission;
- a valid request does not establish trust; and
- runtime enforcement is deferred to a later security design.

## Dependencies

Each dependency contains a plugin ID and a non-empty PEP 440 version specifier.
Dependencies are normalized and sorted by ID. A plugin cannot depend on itself,
and each dependency ID may appear only once.

E-013.2 evaluates dependencies against compatible metadata already present in
the discovered catalog. It reports missing IDs, unsatisfied version ranges, and
cycles. A satisfied edge selects the highest matching version deterministically.
It does not download packages, install dependencies, or solve a remote package
repository.

## Discovery and catalog

The default project root is `Plugins/`. The CLI can inspect multiple explicitly
approved roots with repeatable `--root` options. Each root has a stable label,
and records and issues retain that provenance.

Discovery is recursive, exact-filename, sorted, and read-only. It ignores VCS,
cache, virtual-environment, dependency, build, distribution, and Rust target
directories. It does not follow symlinked directories and rejects symlinked
manifests.

Automatic bundled and per-user root locations and cross-root precedence remain
deferred. Duplicate ID/version pairs across all roots are always errors; one
source never silently replaces another.

Missing and symlinked roots are explicit issues. Root IDs and resolved root paths
must be unique.

## Compatibility and validation phases

Validation runs in ordered phases:

1. structural discovery and duplicate detection;
2. SDK API-level compatibility classification; and
3. dependency constraint selection and cycle detection.

A failed phase stops later phases to avoid cascading noise. SDK compatibility
does not imply trust. Dependency satisfaction means only that matching metadata
is present.

## Catalog resolution

The catalog provides:

- stable ID/version inventory;
- exact-version resolution;
- highest-version default resolution; and
- highest-version resolution satisfying a PEP 440 specifier.

Incompatible SDK records cannot be registered.

## Shared manifest family

E-012 registers plugin manifests as:

```text
stable id:       ups.plugin
kind:            plugin
filename:        plugin-manifest.yaml
current schema:  1
readable schema: 1
cardinality:     many
```

The Plugin System owns schema meaning. The shared Manifest System owns recursive
inventory, hashing, compatibility classification, and cardinality.

## Commands

```powershell
python -m Engineering plugin list
python -m Engineering plugin inspect example.echo
python -m Engineering plugin inspect example.echo --version 1.0.0
python -m Engineering plugin validate
python -m Engineering plugin validate --root C:\path\to\approved\plugins
python -m Engineering plugin dependencies --root C:\project\plugins --root C:\user\plugins
python -m Engineering generate plugin example.echo --capability commands --dry-run
python -m Engineering generate plugin example.echo --capability commands
python -m Engineering plugin package inspect example.echo-1.0.0.ups-plugin.zip
python -m Engineering plugin install plan example.echo-1.0.0.ups-plugin.zip --approve-sha256 SHA256
python -m Engineering plugin runtime digest example.echo
python -m Engineering plugin runtime probe example.echo --approve-sha256 SHA256 --acknowledge-full-trust
```

The generation command writes only below one direct child of `Plugins/`. It
uses the built-in E-009 `plugin.python-basic` definition, and E-008 performs
rendering, path safety checks, conflict handling, dry runs, and writes. Use
repeatable `--permission` and `--dependency ID=SPECIFIER` options as needed.
`--overwrite` is explicit; the default preserves differing existing files.
Generation never imports, activates, installs, or grants trust to a plugin.
Package inspection and installation planning are also read-only. The runtime
`digest` command is read-only. The `probe` command is the only execution
adapter: it explicitly activates and then deactivates one plugin inside that CLI
process. No command extracts, installs, updates, removes, signs, trusts
persistently, or configures automatic loading.
