# Build System

UPS build orchestration is implemented by `Engineering/BuildSystem`.

The E-010 build verifies the repository through a deterministic plan:

1. Project structure and required-file validation.
2. In-memory Python syntax compilation for Backend and Engineering sources.
3. Structured build reporting.
4. A deterministic manifest for successful builds.

Use:

```text
python -m Engineering build plan
python -m Engineering build run --dry-run
python -m Engineering build run
python -m Engineering build clean
```

Backend/frontend packaging, wheels, PyInstaller, Tauri, signing, installers,
and publishing belong to E-011 Release and Packaging.
