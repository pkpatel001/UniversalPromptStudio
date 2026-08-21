# ADR-0007 — Reproducible Frontend Packaging

**Date:** 2026-08-21
**Status:** Accepted
**Milestone:** E-011.2

## Context

E-011.1 established safe Python package creation but deferred the frontend
because no package-manager lockfile existed. The repository already uses npm in
its Vite and Tauri commands, and npm is available in the supported development
environment. A production Vite artifact can therefore be made reproducible
without claiming that the incomplete Rust/Tauri application is bundle-ready.

The originally declared Vite 5 range resolves to dependencies with known npm
audit advisories. The frontend dependency baseline must not freeze those
advisories into the first committed lockfile.

## Decisions

### 1. npm is the frontend package manager

`Frontend/package-lock.json` is committed at lockfile schema version 3.
`package.json` records npm 11.16.0 as the package-manager baseline and declares
the Node versions supported by Vite 8.

### 2. Vite is upgraded before locking

Vite is upgraded to 8.2.2 before generating the lockfile. The resolved graph
must pass `npm audit` with no known vulnerabilities at the checkpoint boundary.

### 3. Release builds use `npm ci`

The frontend builder runs `npm ci` against the committed lockfile and then
`npm run build`. It does not update dependency declarations or the lockfile
during release execution.

### 4. The Vite distribution is a deterministic ZIP

Only files under `Frontend/dist/` are packaged. ZIP entries use sorted relative
paths, a fixed timestamp, stable file permissions, and a fixed compression
level. The archive is written under `release/packages/frontend/`.

### 5. Frontend archives are inspected

The release inspector verifies that the archive contains `index.html`, at least
one JavaScript asset, and at least one CSS asset. Existing unsafe-path and
secret-bearing-name checks apply to the frontend archive.

### 6. Tauri remains deferred

This checkpoint does not run `tauri build` and does not create a desktop bundle.
That work still requires a valid Rust crate, `Cargo.toml`, `Cargo.lock`, Rust
tooling, platform bundle verification, and later signing decisions.

## Consequences

- Frontend dependencies are repeatable through `npm ci`.
- The release manifest and checksum file now cover three local artifacts.
- Vite output can be distributed independently of a desktop shell.
- Node dependency installation remains a local build action, not publication.
- Tauri readiness remains explicit rather than simulated.
