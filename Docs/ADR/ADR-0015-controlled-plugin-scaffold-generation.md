# ADR-0015: Controlled Plugin Scaffold Generation

**Status:** Accepted  
**Milestone:** E-013.3

## Context

E-013.1 and E-013.2 established canonical plugin metadata, discovery,
compatibility, catalogs, and local dependency checks without executing code.
Plugin authors now need a deterministic starting layout, but generation must
not duplicate the E-009 template or E-008 filesystem boundaries and must not
prematurely define installation, trust, or runtime behavior.

## Decision

### Ownership and composition

`Engineering.PluginSystem.PluginScaffoldService` owns plugin-specific input
validation and canonical manifest composition. It invokes the built-in E-009
`plugin.python-basic` template through `TemplateExecutor`. E-009 owns template
definition resolution, declared variables, artifact composition, and the
`.ups-artifact-manifest.json` record. E-008 owns rendering, path validation,
preflight, conflict policy, dry runs, and filesystem writes.

The CLI is a thin adapter. It does not render or write files directly.

### Bounded layout

One invocation targets exactly one direct child of the project `Plugins/`
root. The default for `example.echo` is `Plugins/example-echo`. Absolute paths,
traversal, nested destinations, and destinations outside `Plugins/` are
rejected before template execution.

The template produces exactly:

```text
plugin-manifest.yaml
plugin.py
README.md
```

After a successful non-dry run, E-009 also writes its existing artifact
manifest. The generated plugin manifest uses schema 1 and is read back through
`PluginManifestReader` as a postcondition.

### Controlled inputs and conflicts

The generator accepts plugin identity, name, description, restricted canonical
version, SDK API level, capabilities, permissions, dependencies, and an
optional public Python class name. Domain models validate every metadata value.
Capabilities, permissions, and dependencies are unique and sorted. The entry
point is generator-controlled as `plugin:ClassName`.

Dry run performs E-008 preflight without writing. Differing existing files are
conflicts by default. Replacement requires explicit `--overwrite`; identical
files remain unchanged.

### Passive source skeleton

`plugin.py` contains only a passive class skeleton and documentation. Scaffold
generation never imports, resolves, instantiates, activates, or executes it.
The skeleton does not claim a runtime lifecycle contract because that contract
is deferred.

## Security boundary

- Output is restricted to the tracked project plugin root.
- E-008 retains project containment, protected-path, and secret-context checks.
- Manifest fields remain metadata only; permissions are not grants.
- No network access, dependency download, installation, packaging, signing,
  trust decision, entry-point loading, or runtime execution occurs.
- Generated metadata does not establish safety or trust.

## Consequences

- Plugin authors receive a deterministic, validated, conflict-safe scaffold.
- E-013 reuses E-009 and E-008 rather than introducing a second writer.
- Generated artifacts are auditable through the existing E-009 manifest.
- E-013.4 install/package/trust planning and E-013.5 controlled runtime loading
  remain separate checkpoints.
