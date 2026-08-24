# Phase roadmap

## Completed: Engineering Toolkit

E-001 through E-017 are complete. The toolkit now provides repository
configuration, validation, diagnostics, documentation, safe generation,
templates, build/release packaging, manifest inventory, plugin/provider/theme/
workflow SDK boundaries, and controlled self-generation.

The toolkit closure does not mean the Universal Prompt Studio product is
complete. See `ENGINEERING_TOOLKIT_CAPABILITY_MATRIX.md` for exact supported
and deferred scope.

## Current: Application vertical slices

| Sequence | Phase | Outcome |
| --- | --- | --- |
| A-001 | Desktop IPC | Tauri/Vite communicates with the Python application through a typed, allowlisted boundary |
| A-002 | Prompt library | Persistent prompt/project organization, editing, and search |
| A-003 | Prompt execution | Composition and offline reference execution |
| A-004 | Providers | Controlled provider settings, endpoints, credentials, and invocation |
| A-005 | Workflows | Authoring, validation, and bounded execution UI |
| A-006 | Extensibility UI | Supported theme, plugin, and provider lifecycle surfaces |
| A-007 | Product hardening | Import/export, settings, diagnostics, onboarding, accessibility, localization, backup, and distribution polish |

The immediate checkpoint is **A-001.1 — Explicit desktop-to-Python IPC
foundation**. Scope and acceptance guidance are in
`APPLICATION_DEVELOPMENT_HANDOFF.md`.

## Planning rule

Build the thinnest usable end-to-end slice. Extend the Engineering Toolkit only
when that slice demonstrates a specific missing contract.
