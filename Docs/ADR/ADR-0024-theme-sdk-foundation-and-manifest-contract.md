# ADR-0024: Theme SDK foundation and manifest contract

**Status:** Accepted  
**Milestone:** E-015.1

## Context

The frontend currently contains hard-coded colors and a placeholder Theme SDK
document. E-015 must eventually generate and apply themes, but generation and
runtime application need a stable portable contract first. Accepting arbitrary
CSS, scripts, asset paths, or extensible token names in the foundation would
prematurely create sanitization, filesystem, browser, and compatibility risks.

## Decision

### Producer-owned manifest

`Engineering.ThemeSystem` owns schema 1 of the exact filename
`theme-manifest.yaml`. The root contains `schema_version` and one `theme`
mapping. Every field is required and unknown fields are rejected.

The theme mapping contains a vendor-qualified ID, canonical implementation
version, positive Theme SDK API level, bounded name and description, default
appearance, and one or more palettes.

### Fixed appearance vocabulary

Schema 1 recognizes `light`, `dark`, and `high-contrast`. Palette appearances
must be unique and the default appearance must have a corresponding palette.
The high-contrast name is descriptive metadata, not a conformance claim.

### Fixed semantic color contract

Every palette contains canvas, surface, muted surface, text, muted text, border,
primary, primary text, sidebar, sidebar text, and focus colors. Values are
restricted to opaque six-digit hexadecimal form.

Arbitrary CSS properties and custom token names are excluded. Fonts, icons, and
asset paths are also excluded until their packaging and runtime safety rules are
defined.

### Read-only integration

E-012 registers `ups.theme` as a plural manifest family and delegates schema
validation to `ThemeManifestReader`. The read-only command is:

```powershell
python -m Engineering theme inspect MANIFEST
```

Inspection parses safe YAML but does not load assets, generate CSS, modify the
frontend, or apply styles.

## Consequences

- Theme generation and engine work gain stable typed metadata and palette roles.
- Multiple theme manifests can be inventoried by the shared manifest system.
- Schema 1 stays portable and non-executing.
- E-015.2 can add deterministic discovery, SDK compatibility, identity/version
  handling, and catalog resolution.
- A later scaffold checkpoint can reuse E-009 and E-008.
- Fonts, icons, assets, contrast scoring, generation, installation, selection,
  persistence, frontend integration, preview, and runtime application remain
  deferred.
