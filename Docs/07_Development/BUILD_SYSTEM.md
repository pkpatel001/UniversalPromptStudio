# Build System

UPS build orchestration is implemented by `Engineering/BuildSystem`.

The E-010 build verifies the repository through deterministic profiles:

- `backend`: project validation, in-memory Python syntax compilation, and
  backend source inventory.
- `frontend`: project validation and Vite/Tauri configuration readiness.
- `full`: backend and frontend targets with shared dependencies deduplicated.

Every profile produces structured reporting and successful real builds produce
a deterministic manifest.

Use:

```text
python -m Engineering build plan
python -m Engineering build plan --profile frontend
python -m Engineering build run --dry-run
python -m Engineering build run --profile backend
python -m Engineering build run
python -m Engineering build clean
```

Backend/frontend packaging, wheels, PyInstaller, Tauri, signing, installers,
and publishing belong to E-011 Release and Packaging.

The current repository does not commit a frontend dependency lockfile or Rust
`Cargo.toml`, so E-010 validates frontend readiness without claiming to produce
a reproducible Tauri application bundle.
