# Engineering SelfGeneration

**Milestone:** E-017.1
**Status:** Read-only planning implemented

## Definition

Self-generation is the human-reviewed creation of approved Engineering Toolkit
structures through the existing E-009 template and E-008 generation pipeline.
It is not autonomous self-modification. E-017.1 defines the typed request,
allowlist, readiness checks, plan, and dry-run report only. It performs no
rendering and no writes.

## Initial target

The only supported target is one new Engineering subsystem scaffold. A caller
provides bounded identifiers and descriptive text, never a repository
destination or template identifier.

| Artifact family | Derived destination | Required |
|---|---|---|
| Python package | `Engineering/{Package}/__init__.py` | yes |
| Python module | `Engineering/{Package}/{module}.py` | yes |
| Unit test | `Engineering/Tests/test_{module}.py` | yes |
| Subsystem documentation | `Engineering/{Package}/README.md` | yes |
| CLI adapter placeholder | `Engineering/cli/commands/{module}.py` | opt-in |

The associated renderer keys are closed host vocabulary. They are planning
identifiers in E-017.1, not caller-selected Jinja templates or executable code.

## Preconditions

`SelfGenerationPreconditionChecker` verifies exact, regular, non-symlinked
repository evidence for every completed milestone from E-007 through E-016:

| Milestone | Required capability |
|---|---|
| E-007 | Documentation generation |
| E-008 | Safe code-generation planning and execution |
| E-009 | Template definitions and artifact manifests |
| E-010 | Build planning and evidence |
| E-011 | Release planning and verification |
| E-012 | Shared manifest validation |
| E-013 | Controlled plugin scaffolding |
| E-014 | Controlled provider scaffolding |
| E-015 | Controlled theme scaffolding |
| E-016 | Controlled workflow scaffolding and execution |

Missing evidence blocks readiness. Existing allowlisted destinations also block
the default no-overwrite plan.

## Planning API

```python
from pathlib import Path

from Engineering.SelfGeneration import (
    SelfGenerationPlanner,
    SelfGenerationRequest,
)

request = SelfGenerationRequest(
    package_name="ExampleSystem",
    module_name="example_service",
    display_name="Example System",
    description="A bounded Engineering subsystem.",
    include_cli_adapter=False,
)
report = SelfGenerationPlanner(Path.cwd()).dry_run(request)

print(report.summary)
for line in report.lines:
    print(line)
```

Both the plan and report are immutable and deterministically ordered. Planning
reads only fixed repository evidence and destination state. It does not import
milestone implementations, resolve templates, render content, create
directories, or write files.

## Deferred to E-017.2

- approved E-009 template definitions and assets;
- execution through E-009 and E-008;
- transactional writes and rollback;
- default no-overwrite enforcement during execution;
- `.ups-artifact-manifest.json` evidence;
- check/drift mode;
- reproducibility and post-generation structural/import verification.

Automatic commits, pushes, releases, dependency installation, arbitrary
commands, arbitrary paths, and arbitrary templates are outside E-017.
