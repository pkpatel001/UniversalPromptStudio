# Self-Generation Planning SDK

E-017.1 provides a Python planning API for one controlled Engineering subsystem
scaffold. It is read-only: no E-008 engine, E-009 executor, renderer, filesystem
writer, Git operation, or command runner is reachable from the planner.

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

## Trust boundary

Self-generation means an allowlisted plan followed, in E-017.2, by the existing
controlled template pipeline and human review. It does not mean that the
toolkit selects its own goals, invents paths or templates, rewrites security
logic, approves changes, or operates Git.

The E-017.1 template keys are closed host identifiers reserved for the next
checkpoint. They do not resolve or execute anything in this checkpoint.
