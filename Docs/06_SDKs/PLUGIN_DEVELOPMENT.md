# Plugin Development

## Current checkpoint

E-013.1 supports authoring and validating plugin metadata. It does not load or
run a plugin. Start with the contract in
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
python -m Engineering manifest inspect
python -m Engineering manifest validate
```

Use `--root` only for a directory you explicitly intend to inspect. Commands
are read-only.

## Interpret results

- `plugin.manifest.invalid` means the plugin-owned schema reader rejected the
  document.
- `plugin.identity.duplicate` means the same ID/version appears more than once.
- `plugin.symlink` means an exact manifest filename is a symlink and was not
  inspected.
- E-012 reports plugin schema failures as `manifest.schema.invalid` while
  retaining the plugin reader's message.

## Security boundary

Capabilities and permissions are descriptive metadata only. They are neither
grants nor enforced restrictions. Passing validation does not mean a plugin is
trusted, isolated, installable, or safe to execute.

Do not build loading or activation logic around E-013.1 inspection. Runtime
work must first define lifecycle, typed registration context, failure isolation,
permission enforcement, and trust policy.

## Future generation

The current `generate plugin` command remains intentionally unimplemented.
When plugin scaffolding is added, it must use an E-009 template definition and
the E-008 generation pipeline instead of writing files directly.
