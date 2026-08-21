# E-010 Build System

The Engineering Build System provides deterministic, dependency-aware build
orchestration. It verifies that the project is ready for packaging without
owning distribution formats, installers, signing, or releases.

## Pipeline

```text
Build targets
    -> dependency planning
    -> validated BuildPlan
    -> fail-fast step execution
    -> BuildReport
    -> successful build manifest
```

The default build currently runs:

1. `build.validate-project` — established project structure rules.
2. `build.python-syntax` — in-memory compilation of Backend and Engineering
   Python sources without writing bytecode.

## Safety and determinism

- Step identifiers are unique and stable.
- Unknown dependencies and dependency cycles fail during planning.
- Failed steps stop execution; remaining steps are reported as skipped.
- Dry-runs perform no build work and never write manifests.
- Unexpected step exceptions become structured failures.
- Successful real builds write `build/build-manifest.json`.
- Build manifests contain no timestamps or absolute machine paths.

## CLI

```text
python -m Engineering build plan
python -m Engineering build run --dry-run
python -m Engineering build run
python -m Engineering build clean
```

`build clean` removes only the canonical ignored `build/` output directory.

## Milestone boundary

E-010 owns build planning, build verification, orchestration, output tracking,
and cleanup. E-011 owns wheels, installers, PyInstaller/Tauri bundles, signing,
release metadata, and publishing.
