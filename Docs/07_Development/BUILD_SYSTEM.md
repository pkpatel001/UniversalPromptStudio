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

E-011 Release and Packaging consumes a successful full build and creates local
Python sdist/wheel, deterministic frontend ZIP, and unsigned Windows NSIS
artifacts with a release manifest and checksums.

The repository commits npm and Cargo lockfiles plus the Tauri manifest. Run the
frontend production build and `cargo check --locked` as independent acceptance
gates; E-010 itself validates readiness and records deterministic build evidence.
Signing, publishing, Git tags/releases, updater metadata, and registry uploads
remain outside the local build and release systems.
