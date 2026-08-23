# Universal Prompt Studio Theme SDK

## Scope through E-015.1

E-015.1 establishes portable declarative theme identity, versions, SDK
compatibility metadata, recognized appearances, and strict semantic color
palettes. Reading or inspecting a theme never loads an asset, parses or injects
CSS, modifies the frontend, or applies styles.

## Manifest schema 1

Each theme uses the exact filename `theme-manifest.yaml`:

```yaml
schema_version: 1
theme:
  id: example.slate
  name: Slate
  version: 1.0.0
  sdk_version: 1
  description: A portable slate theme.
  default_appearance: light
  palettes:
    - appearance: light
      colors:
        canvas: "#F6F8F8"
        surface: "#FFFFFF"
        surface_muted: "#EDF3F2"
        text: "#182026"
        text_muted: "#627277"
        border: "#DFE7E7"
        primary: "#276A73"
        primary_text: "#FFFFFF"
        sidebar: "#12181C"
        sidebar_text: "#F7FBFB"
        focus: "#2F7D89"
```

Every root, theme, palette, and colors key is required and exact. Unknown keys
are rejected. A manifest contains at least one palette, palette appearances are
unique, and `default_appearance` must have a matching palette.

## Identity and versions

Theme IDs are stable lowercase vendor-qualified identifiers such as
`ups.slate` or `example.high-contrast`. Theme versions use canonical PEP 440
with exactly three release components. `sdk_version` is a positive integer API
level independent of the manifest schema and theme implementation version.

The current Theme SDK metadata API level is 1. Compatibility classification
and multi-version resolution are deferred to E-015.2; E-015.1 records and
validates the declared level.

## Appearances

Schema 1 recognizes:

- `light`
- `dark`
- `high-contrast`

These values describe a palette category only. A high-contrast declaration is
not a claim of WCAG conformance. Automated contrast analysis and accessibility
policy require a later checkpoint.

## Semantic colors

Every palette defines the same fixed roles: canvas, surface, muted surface,
text, muted text, border, primary, primary text, sidebar, sidebar text, and
focus. Values must be opaque six-digit hexadecimal colors (`#RRGGBB`).

Schema 1 deliberately excludes arbitrary CSS properties and custom token names.
That keeps manifests portable and prevents the metadata reader from becoming a
CSS execution or sanitization boundary.

## Shared manifest family

E-012 registers theme manifests as:

```text
stable id:       ups.theme
kind:            theme
filename:        theme-manifest.yaml
current schema:  1
readable schema: 1
cardinality:     many
```

The theme-owned reader remains the source of schema meaning. Shared manifest
inspection delegates structural validation without reinterpreting the theme.

## Commands

```powershell
python -m Engineering theme inspect C:\path\to\theme-manifest.yaml
python -m Engineering manifest types
python -m Engineering manifest inspect --root C:\path\to\project
python -m Engineering manifest validate --root C:\path\to\project
```

`theme inspect` validates one exact document and reports identity, version,
default appearance, and available palettes. It performs no writes or runtime
theme operations.

## Deferred work

Fonts, icons, asset paths, arbitrary/custom tokens, contrast scoring,
multi-root discovery, SDK compatibility classification, catalog resolution,
scaffold generation through E-009/E-008, installation, selection, persistence,
CSS variable emission, frontend integration, live preview, and runtime theme
application remain later E-015 work.
