# Plugin Development

## Current checkpoint

E-013.2 supports authoring, multi-root discovery, SDK compatibility checks, and
local metadata dependency validation. It does not load or run a plugin. Start
with the contract in
`Docs/06_SDKs/PLUGIN_SDK.md` and the architecture decision in ADR-0013.

## Project layout

Place each project plugin below the tracked `Plugins/` root:

```text
Plugins/
└── example-echo/
    ├── plugin-manifest.yaml
    └── example_echo/
        └── plugin.py
```

The Python file is illustrative. E-013.1 will validate the entry-point string but
will not read, import, instantiate, or execute that file.

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

Do not build loading or activation logic around E-013 inspection. Runtime
work must first define lifecycle, typed registration context, failure isolation,
permission enforcement, and trust policy.

## Future generation

The current `generate plugin` command remains intentionally unimplemented
until E-013.3.
When plugin scaffolding is added, it must use an E-009 template definition and
the E-008 generation pipeline instead of writing files directly.
