# ADR-0008 — Tauri Desktop Packaging

**Date:** 2026-08-21
**Status:** Accepted
**Milestone:** E-011.3

## Context

E-011.2 created a reproducible production frontend archive while explicitly
deferring desktop packaging. The repository did not yet contain a Rust crate or
locked Rust dependency graph, so a desktop installer could not be represented
truthfully.

Tauri v2 requires Rust and platform-native prerequisites. On Windows, the
supported toolchain is the stable MSVC Rust target with Microsoft C++ Build
Tools and WebView2. Tauri produces Windows setup executables through NSIS and
Microsoft installers through WiX; only one format is needed for this checkpoint.

## Decisions

### 1. `src-tauri` is a real Rust application

`Frontend/src-tauri/` contains `Cargo.toml`, `Cargo.lock`, `build.rs`, Rust entry
points, an explicit desktop capability, and generated Windows icon resources.
The committed Cargo lockfile is the authoritative Rust dependency graph.

### 2. Stable Windows MSVC is the desktop toolchain

Desktop release preconditions require `rustup`, `rustc`, and `cargo`; an active
Windows MSVC Rust toolchain; Microsoft C++ Build Tools; and WebView2. Missing
host prerequisites are reported before a release build begins.

### 3. NSIS is the first desktop package format

The Tauri configuration enables only the NSIS target. Local builds produce a
current-user `*-setup.exe` under `release/packages/desktop/`. MSI, signing,
updater metadata, and publication remain separate decisions.

### 4. Desktop artifacts are inspected as PE executables

The release inspector verifies the DOS and PE signatures without executing the
installer, records its size and SHA-256 digest, and includes it in the common
release manifest and checksum file.

### 5. One locked frontend installation feeds both artifacts

When a frontend ZIP and desktop installer are requested together, the desktop
build runs `npm ci` and Tauri's configured Vite build. The frontend builder then
archives that same production distribution instead of installing and compiling
the frontend a second time.

## Consequences

- A local release contains four independently identified artifacts: source
  distribution, wheel, frontend ZIP, and Windows NSIS setup executable.
- Desktop packaging now proves the Rust, web, and native Windows layers together.
- The NSIS installer is unsigned at this checkpoint and Windows may display a
  publisher warning until a later signing decision is implemented.
- Desktop packages remain local; no installer is published or uploaded.
