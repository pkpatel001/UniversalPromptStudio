# Theme Development

## Current checkpoint

Through E-015.6, the toolkit supports strict declarative manifest authoring,
shared-manifest inventory, explicit-root discovery, Theme SDK compatibility,
deterministic catalog resolution, appearance filtering, and controlled scaffold
generation plus typed token compilation, reversible frontend application,
catalog transport, and opt-in preferences. Begin with `THEME_SDK.md`, ADR-0024
through ADR-0029.

## Generate a starting theme

Preview a new project-local scaffold without writing files:

```powershell
python -m Engineering generate theme example.slate --dry-run
```

Generate one or more deterministic built-in palettes:

```powershell
python -m Engineering generate theme example.slate --appearance light --appearance dark
```

The default destination is `Themes/example-slate/`. A custom `--destination`
must still name one direct child of `Themes/`. Existing differing files fail by
default; use `--overwrite` only after reviewing the planned replacement.

The result contains the strict manifest, an author README, and an E-009 artifact
manifest. Edit palette values afterward and validate the manifest again. The
generator creates no CSS or assets and does not install, select, preview, or
apply the theme.

## Compile runtime tokens

Inspect the exact selector-free declarations for the default palette:

```powershell
python -m Engineering theme tokens .\theme-manifest.yaml
```

Choose another palette only when it is declared by the manifest:

```powershell
python -m Engineering theme tokens .\theme-manifest.yaml --appearance dark
```

The command emits exactly eleven fixed `--ups-color-*` declarations in stable
host order. It writes no file and emits no selector or CSS rule. Treat the
output as a deterministic inspection and integration input, not as an installed
or applied theme. Do not add arbitrary token names to schema 1.

## Apply and revert a session theme

The application header exposes a Theme selector and Revert theme button. The
selector applies one host-authored light, dark, or high-contrast payload to the
document root. Revert restores the exact colors and selection attributes that
existed before the first theme was applied.

Theme switching is session-only by default. It does not modify manifests, call
Tauri commands, read files, or make network requests. Refreshing or restarting
returns to the stylesheet defaults unless the user explicitly enables the
E-015.6 Remember theme option described below.

Validate the frontend controller and production bundle with:

```powershell
cd Frontend
npm test
npm run build
```

When extending the adapter, retain exact payload keys, the fixed token list,
validate-before-write behavior, atomic rollback, and original-baseline revert.
Do not accept arbitrary CSS property names or use `cssText`, style elements, or
HTML injection for theme application.

## Synchronize the frontend catalog

After adding or changing an approved theme manifest, update and verify the
generated frontend module:

```powershell
python -m Engineering theme sync-frontend --root Themes
python -m Engineering theme sync-frontend --root Themes --check
npm test --prefix Frontend
npm run build --prefix Frontend
```

Commit the manifest and generated module together. Never edit the generated
module by hand. Desktop CI watches `Themes/**` and rejects stale transport data.

## Preference behavior

Selecting a theme remains session-only unless the user checks Remember theme.
The saved record identifies a current catalog selection but does not copy its
tokens. On reload, an exact catalog match is required before application.
Unchecking Remember theme, choosing Default, or using Revert theme clears the
saved record.

Do not persist token values or automatically migrate an unknown preference to a
different version or appearance. Catalog removal must safely return the user to
the default application colors.

## Author a manifest

Create `theme-manifest.yaml` in the future theme directory. Use a stable
vendor-qualified ID, canonical three-component version, SDK API level 1, and at
least one complete palette. The declared default appearance must be present.

Validate the document directly:

```powershell
python -m Engineering theme inspect .\theme-manifest.yaml
```

Inventory theme manifests with the shared E-012 system:

```powershell
python -m Engineering manifest validate --root C:\path\to\project
```

Multiple theme manifests are allowed by E-012. The E-015.2 discovery service
additionally rejects duplicate theme ID/version pairs across all approved
roots.

## Discover and resolve themes

Validate compatible themes below explicit roots:

```powershell
python -m Engineering theme validate --root C:\path\to\themes
python -m Engineering theme list --root C:\path\to\themes
```

Resolve an exact or highest compatible version, optionally requiring palettes:

```powershell
python -m Engineering theme resolve example.slate --root C:\path\to\themes
python -m Engineering theme resolve example.slate --version 1.0.0 --root C:\path\to\themes
python -m Engineering theme resolve example.slate --root C:\path\to\themes --appearance dark
```

Repeat `--root` only for directories you explicitly approve. Root order is not
a priority or fallback policy. Duplicate root IDs, resolved paths, and theme
identities are deterministic errors.

## Palette guidance

Use semantic intent rather than component-specific names. `canvas`, `surface`,
and `surface_muted` establish hierarchy; text roles provide readable content;
primary roles style important actions; sidebar roles cover navigation; and
focus supports keyboard visibility.

Only opaque `#RRGGBB` colors are accepted. Appearance names are limited to
`light`, `dark`, and `high-contrast`. The reader validates structure, not visual
quality or accessibility conformance.

## Security boundary

Do not place CSS, scripts, URLs, file paths, fonts, icons, credentials, or
machine-local values in schema 1. Unknown and secret-like fields are rejected.
Inspection does not load assets, modify `Frontend/src/styles.css`, or apply a
theme. Discovery does not follow symlinks and ignores dependency, cache, VCS,
build, distribution, and Rust target directories. Resolution is metadata-only
and does not establish installation, trust, visual quality, or runtime readiness.
