# Universal Prompt Studio Theme SDK

## Scope through E-015.6

E-015.1 establishes portable declarative theme identity, versions, SDK
compatibility metadata, recognized appearances, and strict semantic color
palettes. E-015.2 adds deterministic multi-root discovery, SDK compatibility
classification, identity/version policy, and appearance-aware catalog
resolution. E-015.3 adds bounded scaffold generation through the shared E-009
and E-008 pipeline. E-015.4 adds deterministic typed token compilation and
selector-free CSS-variable serialization. E-015.5 adds explicit, reversible
frontend application for host-authored selections. Metadata and compilation
remain non-applying; only the frontend controller mutates the fixed properties,
and only after a user action. E-015.6 adds deterministic build-time catalog
transport and opt-in identity-only preference restoration.

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
python -m Engineering theme tokens C:\path\to\theme-manifest.yaml
python -m Engineering theme tokens C:\path\to\theme-manifest.yaml --appearance dark
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

## Runtime token compilation

`theme tokens` reads one strict manifest and compiles either its default palette
or one explicit declared appearance. The immutable result retains the exact
theme ID, version, and appearance and contains every semantic token in fixed
host order:

```text
canvas, surface, surface-muted, text, text-muted, border, primary,
primary-text, sidebar, sidebar-text, focus
```

The serializer maps this closed set to `--ups-color-*` declarations. It emits no
selector, braces, file, asset reference, or arbitrary CSS property. A later
application boundary must decide where and whether to attach the declarations.
Compilation never falls back to another appearance; requesting an undeclared
palette is an error.

## Controlled frontend application

The frontend `ThemeApplicationController` accepts one exact selection payload:

```text
themeId, version, appearance, tokens
```

Every top-level field and all eleven tokens are required, and unknown fields are
rejected before the DOM is changed. Theme IDs, versions, appearances, and opaque
hexadecimal colors are revalidated at the frontend boundary. Token names map
only to the fixed `--ups-color-*` properties.

The first successful application captures the exact baseline property values,
priorities, and `data-ups-*` attributes. Switching themes retains that original
baseline. A failed application restores the previously active snapshot; an
explicit revert restores the original baseline and clears the active selection.
If baseline restoration fails, the controller restores the complete active
snapshot instead of accepting a partial revert.

The current UI offers host-authored light, dark, and high-contrast selections.
Selection remains session-only unless the user explicitly enables the E-015.6
Remember theme option described below. High contrast is an appearance label,
not a WCAG conformance claim.

## Catalog-to-frontend transport

The project-local built-in theme is authored as the strict manifest
`Themes/ups-built-in/theme-manifest.yaml`. Synchronize all compatible palettes
below explicitly approved roots with:

```powershell
python -m Engineering theme sync-frontend --root Themes
python -m Engineering theme sync-frontend --root Themes --check
```

The command always targets exactly
`Frontend/src/generated/theme-catalog.generated.js`; callers cannot select an
arbitrary output. It compiles every palette through `ThemeTokenCompiler`, sorts
by identity, numeric version, and appearance, emits data only, rejects symlinked
output paths, and uses an atomic same-directory replacement. Check mode performs
no writes and fails when the tracked module differs.

The frontend revalidates the generated schema, exact fields, selection count,
stable order, uniqueness, identity, version, appearance, fixed tokens, colors,
and bounded display name before exposing catalog lookups. The desktop packaging
gate checks catalog freshness before running frontend tests and builds.

## Opt-in preference persistence

The Remember theme checkbox is disabled until a theme is actively selected. If
enabled, the browser-local record contains exactly:

```text
schemaVersion, themeId, version, appearance
```

No token, color, CSS, path, or manifest content is stored. On startup, the
identity is restored only when it exactly resolves in the current transported
catalog; the current catalog tokens are then revalidated and applied through the
E-015.5 controller. Missing, malformed, oversized, unknown, or unavailable
preferences are not applied. Selecting Default, reverting, or opting out clears
the record.

## Controlled external-theme installation

External themes use a canonical `<theme-id>-<version>.ups-theme.zip` containing
only root `theme-manifest.yaml`. Inspect the archive and copy its displayed
SHA-256 through an independently reviewed workflow before planning or applying:

```powershell
python -m Engineering theme package inspect .\example.slate-1.0.0.ups-theme.zip
python -m Engineering theme install plan .\example.slate-1.0.0.ups-theme.zip --approve-sha256 SHA256 --acknowledge-external-theme
python -m Engineering theme install apply .\example.slate-1.0.0.ups-theme.zip --approve-sha256 SHA256 --acknowledge-external-theme --source-label reviewed-local
```

The installer derives `Themes/Installed/<id>/<version>`, refuses existing or
duplicate identities, and writes `theme-installation.json` with source label,
package identity, exact digests, and the approval policy. The label records what
the caller asserted; it does not authenticate a publisher. Installation does not
sync the generated frontend catalog or activate the theme. Those remain separate
explicit actions.

## Deferred work

Fonts, icons, asset paths, arbitrary/custom tokens, contrast scoring,
signatures, authenticated publishers, update/removal and revocation workflows,
live preview, asset handling, and accessibility certification remain later work.
