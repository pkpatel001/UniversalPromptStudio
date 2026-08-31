# ADR-0041: Locked Python sidecar and installed lifecycle

**Status:** Superseded by ADR-0042
**Date:** 2026-08-24

## Context

A-001.1 proved the bounded desktop-to-Python protocol but debug builds depended
on a system Python and compile-time checkout, while release builds failed
closed. That was not an installed application lifecycle.

Tauri requires external binaries to be declared with `bundle.externalBin` and
named with a target-triple suffix. Its shell plugin can resolve that declared
sidecar from Rust. Frontend shell permissions are unnecessary because the
webview never owns process lifecycle.

## Decision

- Freeze `Scripts/ups_sidecar.py` with PyInstaller 6.22.2 and a hash-locked
  Windows x86_64 build/runtime dependency set.
- Name the output `universal-prompt-studio-backend-$TARGET_TRIPLE.exe` and
  declare the suffix-free base through Tauri `externalBin`.
- Build the sidecar before Tauri development and release builds.
- Initialize the official shell plugin only for Rust-owned lifecycle management;
  retain `core:default` as the webview's complete capability set.
- Clear inherited process environment and restore only `SystemRoot`, `TEMP`, and
  `TMP`, which the Windows one-file runtime requires.
- Verify exact sidecar identity, application version, protocol version,
  readiness capability, schema, and correlation before returning readiness.
- Kill and discard a failed child; the next user readiness action starts a new
  declared sidecar.
- Generate a sidecar checksum manifest, bundle it as a resource, and stage the
  executable as a separately inspected `desktop-sidecar` release artifact.

## Consequences

Development no longer falls back to a system interpreter. A fresh checkout must
have Python and the locked build wheels available to produce the sidecar, but an
installed application needs neither. The release manifest grows from four to
five artifacts. Windows NSIS remains unsigned. Other target triples require
their own platform-native locked build and acceptance evidence before support is
claimed.

At the A-001.2 boundary, the application command surface remained
readiness-only. ADR-0042 supersedes that application-layer lifecycle with the
versioned app-data SQLite prompt library.

## References

- <https://v2.tauri.app/develop/sidecar/>
- <https://v2.tauri.app/plugin/shell/>
- <https://v2.tauri.app/security/capabilities/>
