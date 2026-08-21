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
    -> Python, npm/Vite, and Rust/Tauri package builders
    -> artifact inspection and SHA-256 checksums
    -> ReleaseManifest and ReleaseReport
    -> independent manifest, package-set, and checksum verification
```

The supported local formats are Python source distributions, Python wheels, a
deterministic ZIP of the production Vite frontend, and a Windows NSIS setup
executable built by Tauri v2. npm and Cargo lockfiles establish reproducibility
for the frontend and Rust dependency graphs.

## Safety

- The Git working tree must be clean.
- Versions and package metadata must agree.
- Python packaging tools and npm must already be installed.
- Desktop packaging additionally requires stable Rust for Windows MSVC,
  Microsoft C++ Build Tools, and WebView2.
- Frontend dependency installation uses only the committed npm lockfile.
- Release execution never accesses a publisher.
- Output is restricted to the ignored `release/` directory.
- Existing output is rejected unless `--overwrite` is explicit.
- Dry-runs do not build packages or write release artifacts.
- Archives are inspected without extraction and reject unsafe or secret-bearing
  member paths.
- Frontend ZIP entries use stable ordering, timestamps, permissions, and
  compression settings.
- Desktop installers must have valid DOS and PE executable signatures.
- Manifests contain relative paths, sizes, formats, and SHA-256 hashes without
  timestamps or machine identifiers.
- Post-build verification rejects missing, unexpected, unsafe, duplicate, or
  modified artifacts and requires a canonical checksum file.

## CLI

```text
python -m Engineering release plan
python -m Engineering release run --dry-run
python -m Engineering release run
python -m Engineering release run --overwrite
python -m Engineering release verify
python -m Engineering release clean
```

`release clean` removes only the canonical ignored `release/` output directory.

The NSIS package produced by E-011.3 is intentionally unsigned. Signing,
publication, MSI packaging, and updater metadata remain outside this checkpoint.

## Automation

`Scripts/package-desktop.ps1` is the local and CI acceptance entry point. The
GitHub Actions workflow in `.github/workflows/desktop-package.yml` runs it on a
Windows 2025 runner and retains the verified unsigned `release/` directory for
14 days. The workflow has read-only repository permissions and cannot create a
GitHub Release or publish packages.
