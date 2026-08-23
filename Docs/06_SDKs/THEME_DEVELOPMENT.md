# Theme Development

## Current checkpoint

E-015.1 supports strict declarative manifest authoring, shared-manifest
inventory, and read-only inspection. Begin with `THEME_SDK.md` and ADR-0024.

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

Multiple theme manifests are allowed. E-015.1 does not yet resolve duplicate
theme identities or versions because the theme discovery/catalog contract is a
later checkpoint.

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
theme.
