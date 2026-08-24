# Engineering SelfGeneration

**Milestone:** E-017 (closed at E-017.3)
**Status:** Supported within the bounded scope below

## Definition

Self-generation is the human-reviewed creation of approved Engineering Toolkit
structures through the existing E-009 template and E-008 generation pipeline.
It is not autonomous self-modification. E-017.1 defines the typed request,
allowlist, readiness checks, plan, and dry-run report. E-017.2 adds execution
through E-009/E-008, transaction rollback, manifest evidence, and no-write
drift verification.

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

## Controlled execution and verification

`SelfGenerationService.execute(plan)` accepts only the current unchanged ready
plan. It selects one of two fixed E-009 definitions, requires two byte-identical
E-008 previews, and then writes with default no-overwrite behavior. Successful
execution records `.ups-artifact-manifest.json` under the generated package.

Any artifact write, manifest write, structural check, isolated import, or
reproducibility failure removes the new exact files and newly created empty
directories. An incomplete rollback is reported separately.

`SelfGenerationService.check(request)` performs a no-write drift check against
both the recorded manifest hashes and content rendered from the current
approved templates. It also parses and compiles every generated Python file and
imports the package through a temporary bytecode-disabled namespace.

## CLI

```powershell
python -m Engineering generate engineering ExampleSystem example_service --dry-run
python -m Engineering generate engineering ExampleSystem example_service
python -m Engineering generate engineering ExampleSystem example_service --check
```

Add `--cli-adapter` consistently to all three commands when the accepted plan
includes the passive CLI placeholder. No overwrite option exists.

E-017.3 closes the Engineering Toolkit phase. Future changes to this subsystem
require a concrete application-development need. Automatic commits, pushes,
releases, dependency installation, arbitrary commands, arbitrary paths, and
arbitrary templates remain outside E-017.

The next checkpoint is A-001.1, the explicit desktop-to-Python IPC foundation.
