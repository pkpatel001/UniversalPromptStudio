# ADR-0029: Controlled Theme Catalog Transport and Opt-In Preferences

**Status:** Accepted  
**Milestone:** E-015.6

## Context

E-015.5 applies only strict host-authored selections and deliberately excludes
catalog transport and persistence. The packaged Tauri frontend does not embed
the Python Engineering Toolkit, and duplicating YAML parsing and Theme SDK rules
in Rust or JavaScript would create competing sources of truth.

Users also need an optional remembered appearance, but persisting token values
would allow stale data to survive catalog changes and would blur identity
selection with trusted runtime content.

## Decision

### Build-time catalog transport

`ThemeFrontendCatalogCompiler` accepts only an SDK-compatible `ThemeCatalog`.
Every declared palette is compiled through the E-015.4 `ThemeTokenCompiler` and
transported with validated identity, bounded display name, exact version,
appearance, and the closed eleven-token set.

`ThemeFrontendCatalogSerializer` produces a deterministic data-only ES module.
Selections use stable theme ID, numeric version, and appearance order. The
tracked built-in manifest is the palette source of truth; duplicated handwritten
JavaScript presets are removed.

`ThemeFrontendCatalogSynchronizer` owns exactly one output:

```text
Frontend/src/generated/theme-catalog.generated.js
```

The output cannot be redirected. Symlinked path components and oversized
existing files are rejected. Updates use an fsynced same-directory temporary
file and atomic replacement. Check mode performs no writes and reports drift.

The frontend independently validates the generated envelope, schema, count,
exact fields, stable order, uniqueness, display name, identity, version,
appearance, token names, and colors before exposing lookups.

### Preference record

`ThemePreferenceStore` uses injected browser storage and writes only after an
explicit Remember theme action. The bounded schema-1 record contains:

```text
schemaVersion
themeId
version
appearance
```

Tokens are never persisted. On startup, the stored identity must resolve exactly
in the current transported catalog. Current catalog tokens are then passed
through the E-015.5 validation and application controller. Invalid, malformed,
oversized, unknown, or unavailable preferences are not applied.

Opt-out, selecting Default, and Revert theme clear the record. There is no
implicit version upgrade, appearance fallback, or migration.

### Build enforcement

Desktop packaging checks generated catalog freshness before frontend tests and
the production build. Workflow path filters include `Themes/**`, so manifest
changes cannot bypass this gate.

No Tauri command, permission, capability, runtime filesystem access, YAML parser,
or network access is added.

## Security boundary

Transport is a build-time data flow from already validated compatible manifests,
not a runtime installation channel. Frontend validation is defense in depth and
does not grant publisher trust. Preference data selects a current catalog entry;
it cannot supply token values or CSS.

Browser-local storage is not a secret store and must contain no credentials or
sensitive data. This checkpoint stores only non-sensitive theme identity.

## Consequences

- The manifest catalog is now the single source for bundled theme palettes.
- Generated frontend data is reproducible, drift-checked, and independently
  validated.
- Remembered themes follow current catalog tokens instead of stale copied colors.
- Users must explicitly opt in and can return to defaults by three clear paths.
- External theme installation, signatures, provenance, migration, assets, live
  preview, accessibility certification, and untrusted-theme policy remain
  deferred.
