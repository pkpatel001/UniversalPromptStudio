# Plugin Development

## Current checkpoint

E-013.4 supports controlled scaffold generation in addition to authoring,
multi-root discovery, SDK compatibility checks, and local metadata dependency
validation. It also inspects bounded package archives and produces read-only
installation plans. It does not install, load, or run a plugin. Start
with the contract in
`Docs/06_SDKs/PLUGIN_SDK.md` and the architecture decision in ADR-0013.

## Project layout

Place each project plugin below the tracked `Plugins/` root:

```text
Plugins/
└── example-echo/
    ├── plugin-manifest.yaml
    ├── plugin.py
    ├── README.md
    └── .ups-artifact-manifest.json
```

The Python file is a passive skeleton. E-013 validates the entry-point string
but does not import, instantiate, activate, or execute that file.

## Generate a scaffold

Preview without writing:

```powershell
python -m Engineering generate plugin example.echo --capability commands --dry-run
```

Generate the scaffold:

```powershell
python -m Engineering generate plugin example.echo --name "Echo Plugin" --capability commands
```

The default destination is `Plugins/example-echo`. A custom `--destination`
must still name one direct child of `Plugins/`. Use repeatable `--capability`,
`--permission`, and `--dependency example.base=">=1,<2"` options. Existing
different files are conflicts unless `--overwrite` is explicitly supplied.

## Author a manifest

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
  permissions: []
  dependencies: []
```

Use all required keys. Keep capabilities, permission requests, and dependencies
unique. Do not place tokens, passwords, credentials, private keys, shell
commands, absolute paths, traversal paths, or machine-local configuration in a
manifest.

## Validate metadata

```powershell
python -m Engineering plugin validate
python -m Engineering plugin list
python -m Engineering plugin inspect example.echo
python -m Engineering plugin dependencies
python -m Engineering manifest inspect
python -m Engineering manifest validate
```

Use `--root` only for a directory you explicitly intend to inspect. Commands
are read-only.

## Inspect a package and plan installation

A canonical package is named `example.echo-1.0.0.ups-plugin.zip`, has no
enclosing directory, and contains root `plugin-manifest.yaml` plus the declared
entry-point module. Inspect it without extraction:

```powershell
python -m Engineering plugin package inspect example.echo-1.0.0.ups-plugin.zip
```

Obtain the expected SHA-256 through an independent, trusted channel, compare it
with the inspection result, and pass that independently obtained digest when
requesting a plan:

```powershell
python -m Engineering plugin install plan example.echo-1.0.0.ups-plugin.zip --approve-sha256 SHA256
```

The plan checks the existing project `Plugins/` root, canonical target, SDK
compatibility, duplicate identity, and dependency graph. It makes no filesystem
changes. A matching hash confirms exact bytes only; it does not authenticate a
publisher or establish code safety.

## Interpret results

- `plugin.manifest.invalid` means the plugin-owned schema reader rejected the
  document.
- `plugin.identity.duplicate` means the same ID/version appears more than once.
- `plugin.root.missing` or `plugin.root.symlink` means an approved discovery
  root cannot be inspected safely.
- `plugin.symlink` means an exact manifest filename is a symlink and was not
  inspected.
- `plugin.sdk.incompatible` means the metadata is structurally valid but its
  SDK API level is outside the host-supported range.
- `plugin.dependency.missing` means no compatible record exists for a required
  plugin ID.
- `plugin.dependency.unsatisfied` means the ID exists but none of its versions
  satisfy the declared constraint.
- `plugin.dependency.cycle` means selected dependency edges form a cycle.
- E-012 reports plugin schema failures as `manifest.schema.invalid` while
  retaining the plugin reader's message.

## Security boundary

Capabilities and permissions are descriptive metadata only. They are neither
grants nor enforced restrictions. Passing validation does not mean a plugin is
trusted, isolated, installable, or safe to execute.

Do not build loading or activation logic around E-013 inspection or install
plans. Runtime
work must first define lifecycle, typed registration context, failure isolation,
permission enforcement, and trust policy.

## Generation boundary

The generator validates plugin-owned metadata, then delegates the scaffold to
the E-009 template system and E-008 generation pipeline. It does not install,
package, sign, trust, import, or activate the result. E-013.4 does not yet build
archives or extract/install them; it defines and inspects the package boundary
and reports installation readiness only.
