# E-011 Release and Packaging System

The Release System creates inspected local packages from a verified E-010 full
build. It does not publish packages, create Git tags, sign binaries, or create
GitHub releases.

## Pipeline

```text
ReleaseContext
    -> deterministic PackagingPlan
    -> release preconditions
    -> E-010 full build
    -> local Python package builder
    -> archive inspection and SHA-256 checksums
    -> ReleaseManifest and ReleaseReport
```

The first checkpoint supports Python source distributions and wheels. Vite
packaging is deferred until the repository has a committed Node lockfile. Tauri
bundling is deferred until a real Rust project, `Cargo.toml`, and `Cargo.lock`
exist.

## Safety

- The Git working tree must be clean.
- Versions and package metadata must agree.
- Packaging tools must already be installed; release execution never installs
  dependencies or accesses a publisher.
- Output is restricted to the ignored `release/` directory.
- Existing output is rejected unless `--overwrite` is explicit.
- Dry-runs do not build packages or write release artifacts.
- Archives are inspected without extraction and reject unsafe or secret-bearing
  member paths.
- Manifests contain relative paths, sizes, formats, and SHA-256 hashes without
  timestamps or machine identifiers.

## CLI

```text
python -m Engineering release plan
python -m Engineering release run --dry-run
python -m Engineering release run
python -m Engineering release run --overwrite
python -m Engineering release clean
```

`release clean` removes only the canonical ignored `release/` output directory.
