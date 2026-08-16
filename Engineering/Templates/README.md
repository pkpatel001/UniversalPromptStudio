# Engineering Templates and Artifacts

This package is the E-009 template and artifact domain built on the E-008
Code Generation framework.

The separation is deliberate:

- E-009 discovers, describes, versions, validates, and catalogs templates and
  their intended artifacts.
- E-008 plans, renders, checks, writes, and reports generated files.

## Layout

```text
Templates/
├── CodeGeneration/       Jinja2 source templates owned by E-008
├── Definitions/          E-009 *.template.yaml definitions
├── catalog.py            Version-aware in-memory catalog
├── discovery.py          File-backed definition discovery
├── manifest.py           Deterministic artifact manifests
├── models.py             Immutable domain models
├── service.py            E-009 to E-008 request bridge
└── validation.py         Definition and source-reference validation
```

## Definition format

Definitions use the suffix `.template.yaml` and contain three sections:

```yaml
metadata:
  id: project.basic
  name: Basic project artifacts
  version: 1.0.0
  category: project
variables:
  - name: version
    kind: optional
    type: string
artifacts:
  - path: module.py
    template: python.module
    type: source
```

Supported variable kinds are `required`, `optional`, and `defaulted`.
Supported value types are `string`, `integer`, `number`, `boolean`, `list`, and
`mapping`. Supplied values and defaults are checked against their declared
types. Defaulted variables must declare a non-null `default` value.

## Discovery and validation

`DirectoryTemplateDefinitionRepository` recursively discovers definition
files in deterministic order. Each definition is validated before being
returned, including its identity, semantic version, variables, artifact paths,
duplicates, and optional cross-references to the E-008 source repository.

## Artifact manifests

`ArtifactManifestBuilder` converts an E-008 `GenerationReport` into a stable,
JSON-serializable record. Written artifacts include SHA-256 hashes so consumers
can verify generated content without relying on timestamps or machine-specific
metadata.

Manifests can be loaded with `ArtifactManifest.read()` and verified against an
artifact directory with `verify()`. Verification reports missing files and
content-hash mismatches without modifying generated output.

## CLI

Built-in definitions are available through the Engineering CLI:

```text
python -m Engineering generate templates
python -m Engineering generate templates inspect project.basic
python -m Engineering generate templates validate
```

The commands use the same discovery and validation services as programmatic
consumers; the CLI remains a presentation adapter.

See [Engineering/CodeGeneration/README.md](../CodeGeneration/README.md) for
source-template conventions and rendering context details.
