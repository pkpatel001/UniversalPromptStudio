# ADR-0026: Controlled Theme Scaffold Generation

**Status:** Accepted  
**Milestone:** E-015.3

## Context

E-015.1 and E-015.2 established strict declarative theme metadata, shared
manifest integration, discovery, compatibility, and deterministic cataloging.
The Engineering Toolkit now needs a fast, consistent starting point for theme
authors without duplicating rendering, filesystem safety, conflict handling,
dry runs, or artifact tracking already owned by E-008 and E-009.

Theme runtime application is not yet defined. Scaffolding must not invent CSS,
assets, installation, selection, persistence, live preview, or frontend
integration prematurely.

## Decision

### Composition boundary

`ThemeScaffoldService` validates theme-owned inputs and constructs the canonical
schema-1 `ThemeManifest`. It delegates generation to the built-in E-009 template
`theme.declarative-basic`.

E-009 owns the template definition, variables, artifacts, and
`.ups-artifact-manifest.json`. E-008 owns rendering, destination safety,
secret-context checks, conflict policy, dry runs, writes, and generation
reports. The theme subsystem does not write scaffold files directly.

### Generated artifacts

The template generates:

```text
theme-manifest.yaml
README.md
```

E-009 additionally records `.ups-artifact-manifest.json` after a successful
real write. The theme document contains only schema-1 metadata and complete
semantic color palettes. Deterministic built-in starting palettes are available
for `light`, `dark`, and `high-contrast` appearances.

After a successful real generation, the service parses the generated manifest
through the theme-owned reader and requires exact equality with the validated
request.

### Destination policy

Scaffolds are restricted to one direct child of the project-local `Themes/`
directory:

```text
Themes/<theme-directory>/
```

Absolute paths, traversal, deeper nesting, drive syntax, and destinations
outside `Themes/` are rejected. The default directory is derived
deterministically from the theme ID.

### Conflict and dry-run policy

Differing existing files are conflicts by default. Replacement requires an
explicit `--overwrite`. Dry runs execute validation, rendering, and planning
but write no theme directory or artifact manifest.

### CLI

```powershell
python -m Engineering generate theme THEME_ID [OPTIONS]
```

Options include name, description, version, SDK level, default appearance,
repeatable appearances, destination, dry run, and explicit overwrite.

## Security boundary

Generation does not parse or emit CSS, load assets, modify frontend files,
install or select a theme, apply styles, evaluate contrast, execute code, or
grant trust. Built-in palette values are starting data, not an accessibility or
visual-quality certification.

## Consequences

- Theme authors gain a consistent, validated project-local starting structure.
- Theme scaffolding reuses the accepted E-009/E-008 pipeline rather than
  introducing ad-hoc writes.
- Generated artifacts remain traceable and exactly re-verifiable.
- A later checkpoint can define controlled token emission or application at a
  separate boundary.
- Fonts, icons, assets, custom tokens, contrast enforcement, installation,
  selection, persistence, CSS emission, live preview, and frontend application
  remain deferred.
