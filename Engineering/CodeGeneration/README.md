# Engineering CodeGeneration Framework

**Milestone:** E-008
**Status:** Implemented

---

## Purpose

The Code Generation framework provides a deterministic, strongly typed,
template-driven, validation-aware pipeline for producing project artifacts.
All future UPS generators (plugins, providers, themes, workflows) consume
this framework rather than implementing ad-hoc file-writing logic.

## Architecture

```
GenerationRequest
       │
       ▼
GenerationPlanner
       │
       ▼
GenerationPlan ─── preflight ─── render ─── safety ─── write ───▶ GenerationReport
```

### Pipeline phases

1. **Plan** — Validate request structure, detect duplicate destinations,
   check path safety, verify template identifiers exist.
2. **Preflight** — Resolve templates, render all artifacts, validate
   every destination path against safety policies.
3. **Safety** — Reject path traversal, protected files, project
   boundary escapes, and secret key patterns in context.
4. **Conflict detection** — Compare rendered content against existing
   files using the overwrite policy (default: NEVER).
5. **Execution** — Write artifacts via `core/filesystem.py`. Parent
   directories created automatically.
6. **Report** — Structured `GenerationReport` with per-artifact state
   and computed summary.

### Artifact states

| State       | Meaning                                                   |
|-------------|-----------------------------------------------------------|
| `CREATED`   | Destination was absent; file written.                     |
| `UNCHANGED` | Destination exists with identical content; no write.      |
| `OVERWRITTEN` | Destination differs; overwrite policy is `ALLOWED`.    |
| `SKIPPED`   | Artifact deliberately skipped by the planner.             |
| `CONFLICT`  | Destination differs and overwrite is `NEVER`.             |
| `FAILED`    | Error prevented artifact production (template, path, etc).|

## Module overview

| Module          | Responsibility                                         |
|-----------------|-------------------------------------------------------|
| `models.py`     | All domain model types (frozen dataclasses + enums)    |
| `templates.py`  | Template model, repository, directory resolver         |
| `renderer.py`   | Jinja2-based rendering behind a clean abstraction      |
| `planner.py`    | Plan construction and structural validation            |
| `policies.py`   | Path safety, boundary checks, secret protection        |
| `generator.py`  | Generator ABC and built-in StaticGenerator             |
| `registry.py`   | Generator ID → implementation lookup                   |
| `engine.py`     | Central engine executing the full pipeline             |

## Template conventions

Templates live under `Engineering/Templates/CodeGeneration/`:

```
Templates/CodeGeneration/
├── python/
│   ├── module.j2
│   └── package.j2
├── yaml/
│   └── config.j2
└── markdown/
    └── readme.j2
```

### Template ID mapping

```
python.module  → Templates/CodeGeneration/python/module.j2
yaml.config    → Templates/CodeGeneration/yaml/config.j2
```

Template identifiers use dots as path separators. Files use the `.j2`
extension (Jinja2 syntax). The directory structure is the source of truth.

### Template variables

Templates receive a `GenerationContext` with:

| Variable        | Access pattern         | Description                         |
|----------------|------------------------|-------------------------------------|
| Project name    | `{{ project.name }}`   | From Engineering configuration      |
| Project version | `{{ project.version }}`| From Engineering configuration      |
| Generator ID    | `{{ generator.generator_id }}` | Requested generator         |
| Artifact name   | `{{ artifact.name }}`  | Artifact-specific name              |
| Custom values   | `{{ values.key }}`     | Artifact-specific extra variables   |

## Safety policies

### Path safety

- Refuses path traversal (`../`)
- Refuses protected directories (`.git`, `__pycache__`)
- Validates destinations stay within the project root
- All paths resolved via `Path.resolve()` before comparison

### Secret protection

Context values whose keys match sensitive patterns (`api_key`, `token`,
`password`, `secret`, `credential`, `private_key`, `access_key`, `auth`)
must not contain non-empty values. This prevents accidental serialization
of secrets into generated artifacts.

### Overwrite policy

Default: `NEVER` — conflicting destinations produce a `CONFLICT` result
and no file is written. The `ALLOWED` policy must be explicitly opted-in
per `GenerationRequest`.

## Integration points

| Subsystem    | Integration                                          |
|--------------|------------------------------------------------------|
| `core.paths` | Project root discovery via `get_paths()`             |
| `core.filesystem` | All writes via `write_text()`, `ensure_directory()` |
| `core.config` | `project_context_from_config()` factory             |
| `core.validation` | `ValidationIssue`/`ValidationReport` reused     |
| `core.exceptions` | Exception hierarchy extends `EngineeringError`  |
| CLI          | Framework is CLI-independent; no commands added      |

## Public API

```python
from Engineering.CodeGeneration import (
    GenerationEngine,
    GenerationRequest,
    GenerationPlan,
    GenerationReport,
    GenerationContext,
    ArtifactSpec,
    ArtifactState,
    OverwritePolicy,
    DirectoryTemplateRepository,
    TemplateRenderer,
    GeneratorRegistry,
    StaticGenerator,
    auto_generated_header,
)
```

## Design decisions

See [ADR-0003](../../Docs/ADR/ADR-0003-code-generation-framework.md).
