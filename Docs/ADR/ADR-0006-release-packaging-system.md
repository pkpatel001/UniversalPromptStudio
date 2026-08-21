# ADR-0006 — Safe Local Release and Packaging System

**Date:** 2026-08-21
**Status:** Accepted
**Milestone:** E-011
**Follow-up:** ADR-0007 supersedes the Vite portion of decision 8.

## Context

E-010 established deterministic build readiness while deliberately excluding
package formats and publication. E-011 must turn a verified build into portable,
inspectable artifacts without coupling local packaging to GitHub, PyPI, npm,
signing, or marketplace services.

The repository can package Python code now, but it has no committed Node
lockfile and no Rust/Tauri crate manifest. Those constraints prevent truthful
claims of reproducible frontend or desktop bundles.

## Decisions

### 1. Release packaging is a separate subsystem

`Engineering.ReleaseSystem` owns release versions, package plans, preconditions,
builders, artifact inspection, checksums, manifests, and reports. E-010 remains
the owner of build validation and is consumed as a required full-build gate.

### 2. The first package formats are wheel and source distribution

Python packages are built through the standard `build` frontend with isolation
disabled. Required build tools must already be installed, so release execution
does not silently download dependencies.

### 3. Version equivalence is normalized

The human release version is `0.2.0-alpha`. Python packaging normalizes that
version to `0.2.0a0`; preconditions compare parsed versions rather than requiring
ecosystem-specific strings to be byte-identical.

### 4. Package contents are explicit and inspected

Setuptools package-data rules and `MANIFEST.in` include Engineering YAML,
Jinja templates, documentation, and licensing material. Every created archive
is inspected without extraction for required contents, unsafe paths, and
secret-bearing path names.

### 5. Outputs are local, deterministic, and isolated

Release output is restricted to `release/`. Packages are stored under
`release/packages/python/`, checksums under `release/checksums/`, and the stable
record is `release/release-manifest.json`. The manifest contains relative paths,
formats, sizes, and SHA-256 hashes; it excludes timestamps and absolute paths.

### 6. Safety defaults are strict

A dirty working tree, missing full-build evidence, inconsistent metadata,
missing tooling, noncanonical output, or existing output stops packaging.
Overwrite requires an explicit flag. Dry-runs write nothing.

### 7. Publication is not implemented

Git tags, GitHub releases, PyPI/npm uploads, signing, notarization, and
marketplace publication require separate adapters and explicit authorization.

### 8. Frontend and Tauri packages remain deferred

Vite packaging requires a selected package manager and committed lockfile.
Tauri packaging additionally requires a valid Rust project and lockfiles. E-011
does not fabricate these prerequisites.

## Consequences

- CI and future publication adapters can consume the same typed release report
  and deterministic manifest.
- Local package creation is testable without Typer, GitHub, or network access.
- Missing reproducibility prerequisites are reported rather than hidden.
- Publication can be added later without changing the release domain.
