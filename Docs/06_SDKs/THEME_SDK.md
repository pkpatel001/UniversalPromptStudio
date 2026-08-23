# Universal Prompt Studio Theme SDK

## Scope through E-015.3

E-015.1 establishes portable declarative theme identity, versions, SDK
compatibility metadata, recognized appearances, and strict semantic color
palettes. E-015.2 adds deterministic multi-root discovery, SDK compatibility
classification, identity/version policy, and appearance-aware catalog
resolution. E-015.3 adds bounded scaffold generation through the shared E-009
and E-008 pipeline. Reading, discovering, validating, resolving, or generating
a theme never loads an asset, parses or injects CSS, modifies the frontend, or
applies styles.

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

The current Theme SDK metadata API level is 1 and the default host supports
exactly level 1. Structurally valid future levels remain discoverable but are
classified as `too-new`; older unsupported levels are `too-old`.

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

## Discovery and provenance

Theme discovery is recursive, sorted, exact-filename, and read-only below one
or more explicitly approved roots. Each root has a stable ID retained by
records and issues. VCS, cache, virtual-environment, dependency, build,
distribution, and Rust target directories are ignored. Symlinked roots,
directories, and manifests are not followed.

Root IDs and resolved root paths must be unique. Duplicate theme ID/version
pairs across or within roots are errors. Roots have no implicit precedence and
one source never silently replaces another.

## Catalog resolution

The catalog contains SDK-compatible metadata only. It provides stable
identity/version ordering, exact-version resolution, highest-version resolution
when no version is supplied, version inventories, and filtering by one or more
required appearances.

Appearance matching is set inclusion over declared palettes. It does not load
colors, evaluate contrast, or claim frontend compatibility.

## Commands

```powershell
python -m Engineering theme inspect C:\path\to\theme-manifest.yaml
python -m Engineering theme list --root C:\path\to\themes
python -m Engineering theme validate --root C:\project\themes --root C:\approved\themes
python -m Engineering theme resolve example.slate --root C:\path\to\themes
python -m Engineering theme resolve example.slate --root C:\path\to\themes --appearance dark
python -m Engineering generate theme example.slate --dry-run
python -m Engineering generate theme example.slate --appearance light --appearance dark
python -m Engineering manifest types
python -m Engineering manifest inspect --root C:\path\to\project
python -m Engineering manifest validate --root C:\path\to\project
```

`theme inspect` validates one exact document and reports identity, version,
default appearance, and available palettes. It performs no writes or runtime
theme operations. Catalog commands require at least one explicit root and retain
the same non-applying boundary.

## Controlled scaffold generation

`generate theme` validates theme-owned inputs, selects deterministic built-in
palettes for the requested appearances, and delegates rendering and writes to
E-009 and E-008. The destination must be exactly one direct child of the
project-local `Themes/` directory. The default is derived from the theme ID.

```text
Themes/example-slate/
  theme-manifest.yaml
  README.md
  .ups-artifact-manifest.json
```

Different existing files are conflicts unless `--overwrite` is explicit.
`--dry-run` performs validation, rendering, and planning without writing the
directory or artifact manifest. After a successful real generation, the theme
reader verifies that the written manifest exactly equals the validated request.
The built-in palette colors are starting values, not an accessibility or visual
quality certification.

## Deferred work

Fonts, icons, asset paths, arbitrary/custom tokens, contrast scoring,
installation, selection, persistence, CSS variable emission, frontend
integration, live preview, and runtime theme application remain later E-015
work.
