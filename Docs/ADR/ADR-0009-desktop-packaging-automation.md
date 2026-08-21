# ADR-0009 — Desktop Packaging Automation

**Date:** 2026-08-21
**Status:** Accepted
**Milestone:** E-011.4

## Context

E-011.3 established a genuine Windows desktop package through Rust, Tauri v2,
and NSIS. The build was proven locally, but desktop packaging still depended on
one developer machine and the release manifest was trusted after creation
without an independent verification pass.

Automation must preserve the E-011 boundary: it may build and retain unsigned
workflow artifacts, but it must not create tags, GitHub Releases, signatures,
or publication records.

## Decisions

### 1. Windows packaging runs on a bounded GitHub Actions workflow

`.github/workflows/desktop-package.yml` runs on manual dispatch, relevant pull
requests, and relevant pushes to `main`. It uses the explicit `windows-2025`
runner label, read-only repository permissions, concurrency cancellation, and a
45-minute timeout.

### 2. Every action is immutable

GitHub-authored actions are pinned to full commit SHAs. The workflow does not
use moving action tags, third-party cache actions, repository secrets, or a
write-capable token.

### 3. Rust is patch-pinned

`rust-toolchain.toml` selects Rust 1.98.0 for Windows MSVC with the minimal
profile, Clippy, and rustfmt. `Cargo.toml` declares the matching minimum Rust
version, and release preconditions validate this policy.

### 4. CI invokes the repository-owned release pipeline

`Scripts/package-desktop.ps1` runs Python tests and static checks, locked Rust
checks, npm audit, the E-010 full build, the four-format E-011 release build,
and post-build verification. CI does not bypass the release domain through a
separate packaging implementation.

### 5. Completed releases are independently verified

`python -m Engineering release verify` requires exactly one artifact for every
supported format. It rejects unsafe or duplicate manifest paths, missing or
unexpected package files, changed sizes or SHA-256 digests, archive or PE
inspection failures, and a non-canonical `SHA256SUMS` file.

### 6. Workflow artifacts are not releases

The verified `release/` directory is retained as a GitHub Actions workflow
artifact for 14 days with no GitHub Release, tag, updater metadata, signature,
or publication step.

## Consequences

- Every relevant change can prove Windows desktop packaging on a fresh runner.
- Toolchain and action drift are controlled by committed immutable inputs.
- A build cannot pass merely by writing a plausible manifest or checksum file.
- CI artifacts remain unsigned engineering evidence, not distributable releases.
- Signing, provenance attestations, updater support, and publication remain
  separately authorized future checkpoints.
