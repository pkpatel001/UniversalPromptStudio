# ADR-0005 — Deterministic Build System

**Date:** 2026-08-21
**Status:** Accepted
**Milestone:** E-010

## Context

UPS needs a reusable build layer before release packaging is introduced. The
existing CLI contained placeholders for `build run` and `build clean`, while
the development documentation listed backend, frontend, packaging, PyInstaller,
and Tauri without defining an orchestration model.

E-010 must establish how build work is planned, executed, and reported without
prematurely absorbing E-011 release and packaging responsibilities.

## Decisions

### 1. Builds use explicit plans

Every build is represented by an immutable `BuildPlan` containing stable step
identifiers in dependency order. Plans reject duplicate identifiers, unknown
dependencies, and dependency cycles before execution.

### 2. Steps are small domain operations

Each `BuildStep` declares its ID, dependencies, and execution behavior. Steps
return structured results and do not print, parse CLI arguments, or terminate
the process.

### 3. Execution is deterministic and fail-fast

The engine executes plan order exactly. A failed step prevents later work;
remaining steps are recorded as skipped. Unexpected exceptions are translated
into failed step results rather than escaping as partial builds.

### 4. Existing validation is reused

Project build validation consumes the E-004 `Validator` and project rules. The
validation API accepts an explicit context so builds and tests validate the
requested project root rather than an implicit checkout.

### 5. Syntax verification is read-only

Python sources are compiled in memory with `compile()`. The build does not
create `__pycache__` directories or bytecode as a side effect.

### 6. Dry-runs never write

Dry-run steps are reported as skipped/planned. No output directories or build
manifests are written.

### 7. Successful builds produce a manifest

`BuildService` writes `build/build-manifest.json` only after a successful real
build. The manifest is deterministic and excludes timestamps and absolute
machine paths.

### 8. Packaging remains E-011

E-010 verifies and orchestrates build readiness. Wheels, executables, Tauri or
PyInstaller bundles, signing, release versions, and publishing remain outside
this milestone.

## Consequences

- Backend, frontend, documentation, and future packaging checks can be added as
  dependency-aware steps without redesigning the CLI.
- CI can consume structured build reports and deterministic manifests.
- Build failures are reproducible and do not silently continue into packaging.
- Release implementation can consume a verified E-010 build instead of running
  ad-hoc checks.
