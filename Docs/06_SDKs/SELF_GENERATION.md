# Self-Generation SDK

E-017.1 provides read-only planning for one controlled Engineering subsystem.
E-017.2 executes accepted plans through E-009/E-008 and verifies reproducibility
without expanding request authority.

## Request

```python
from Engineering.SelfGeneration import SelfGenerationRequest

request = SelfGenerationRequest(
    package_name="SearchSystem",
    module_name="search_service",
    display_name="Search System",
    description="Engineering support for bounded search operations.",
    include_cli_adapter=True,
)
```

The package and module identifiers are validated. The request has no
`destination`, `relative_path`, `template_id`, command, import path, or
overwrite field.

## Plan and dry run

```python
from pathlib import Path

from Engineering.SelfGeneration import SelfGenerationPlanner

planner = SelfGenerationPlanner(Path.cwd())
plan = planner.plan(request)
report = planner.dry_run(request)

if not report.ready:
    for line in report.lines:
        print(line)
```

The plan contains only immutable request data, derived allowlisted artifacts,
E-007 through E-016 precondition results, and stable blocking issues. Its order
is package, module, test, documentation, then the optional CLI adapter.

A plan is blocked when:

- the supplied root is not a UPS project root;
- required milestone evidence is missing or symlinked;
- an exact derived destination already exists; or
- an exact derived destination traverses a symlink.

Dry-run text is a deterministic projection of the plan and ends with
`No files written.`. It is evidence for review, not authorization to write.

## Execute and verify

```python
from Engineering.CodeGeneration import project_context_from_config
from Engineering.core.config import get_config
from Engineering.SelfGeneration import SelfGenerationService

service = SelfGenerationService.built_in(
    Path.cwd(),
    project_context_from_config(get_config()),
)
result = service.execute(plan)
verification = service.check(request)
```

Execution requires the exact current ready plan and never overwrites. It records
the E-009 artifact manifest, verifies current-template bytes and SHA-256 hashes,
parses/compiles all Python output, and performs an isolated package import.
Failures after writing trigger removal of the new exact artifacts and newly
created empty directories.

Check mode renders twice in memory and verifies existing output without
rewriting it. Historical manifest integrity and current-template
reproducibility are both required.

## Trust boundary

Self-generation remains a host-controlled scaffold operation followed by human
review. Callers cannot select paths, templates, commands, imports, credentials,
or overwrite behavior. Import verification executes only package-bundled
host-authored generated code and is not a sandbox.

E-017.2 performs no Git operation, automatic approval, release, publishing,
dependency installation, network request, credential lookup, subprocess, or
arbitrary command.
