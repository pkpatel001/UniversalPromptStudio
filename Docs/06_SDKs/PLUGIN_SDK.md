# Universal Prompt Studio Plugin SDK

## Scope

The E-013.1 Plugin SDK is a metadata contract. It can describe, validate,
discover, and catalog plugins without loading them. A valid manifest is not a
trust decision and does not make a plugin safe to execute.

Runtime lifecycle, activation, deactivation, permission enforcement,
installation, signatures, packages, remote repositories, marketplaces, and UI
management are not implemented.

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

`sdk_version` is a positive integer API level. Manifest schema 1 currently
supports SDK API level 1. It is deliberately separate from:

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

The existing `Backend.interfaces.Plugin` abstraction remains a placeholder
runtime interface. It is not the E-013.1 manifest contract.

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

E-013.1 does not resolve a dependency graph, download packages, or install
dependencies.

## Discovery and catalog

The default project root is `Plugins/`. The CLI can inspect another explicitly
approved root with `--root`.

Discovery is recursive, exact-filename, sorted, and read-only. It ignores VCS,
cache, virtual-environment, dependency, build, distribution, and Rust target
directories. It does not follow symlinked directories and rejects symlinked
manifests.

Bundled and per-user roots and cross-root precedence are deferred. Duplicate
ID/version pairs are always errors; one source never silently replaces another.

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

## Read-only commands

```powershell
python -m Engineering plugin list
python -m Engineering plugin inspect example.echo
python -m Engineering plugin inspect example.echo --version 1.0.0
python -m Engineering plugin validate
python -m Engineering plugin validate --root C:\path\to\approved\plugins
```

`python -m Engineering generate plugin` remains a placeholder until a later
checkpoint adds an E-009 plugin template and delegates writes to E-008.
