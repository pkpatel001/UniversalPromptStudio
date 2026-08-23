# ADR-0025: Theme discovery, compatibility, and catalog

**Status:** Accepted  
**Milestone:** E-015.2

## Context

E-015.1 established a strict declarative theme manifest but only inspected one
exact document. Theme generation and later application need stable discovery,
provenance, SDK compatibility, duplicate identity policy, and resolution before
any filesystem assets or frontend styles are involved.

## Decision

### Explicit multi-root discovery

`ThemeDiscoveryService` scans one or more explicitly supplied, stable-labeled
roots for the exact filename `theme-manifest.yaml`. Discovery is recursive,
sorted, and read-only. It ignores VCS, cache, virtual-environment, dependency,
build, distribution, and Rust target directories.

Symlinked roots, directories, and manifests are not followed. Missing and
symlinked roots are reported with their stable provenance. Root IDs and resolved
paths must be unique.

### Identity and duplicates

A theme identity is the pair of theme ID and implementation version. Duplicate
pairs within or across roots are explicit validation issues. Root ordering does
not establish precedence and one theme never silently replaces another.

### SDK compatibility

`ThemeSdkContract` defines an inclusive supported API-level range. The default
host supports level 1. Structurally valid manifests remain inspectable when
their SDK is too old or too new, but they are excluded from compatible catalog
results and reported as compatibility issues.

### Deterministic catalog

`ThemeCatalog` contains compatible records only. It resolves an exact version or
the highest version for a theme ID, exposes stable version inventory, and can
require one or more declared appearances. Appearance matching is set inclusion
over palette metadata.

The catalog does not evaluate colors, assets, contrast, CSS, installation, or
runtime readiness.

### Read-only CLI

The commands are:

```powershell
python -m Engineering theme list --root ROOT
python -m Engineering theme validate --root ROOT
python -m Engineering theme resolve THEME_ID --root ROOT
```

Roots are mandatory and repeatable. `resolve` optionally accepts exact version
and repeatable appearance requirements.

## Security boundary

Discovery and resolution do not load assets, parse or emit CSS, modify the
frontend, apply styles, access credentials, or execute code. Metadata
compatibility and appearance matches are not trust, quality, accessibility, or
runtime-readiness decisions.

## Consequences

- Later generation and engine work can consume stable catalog records and root
  provenance.
- Duplicate identities cannot depend on caller root order.
- Future SDK levels remain structurally diagnosable without being accepted.
- E-015.3 can add controlled theme scaffold generation through E-009/E-008.
- Assets, fonts, icons, contrast enforcement, installation, selection,
  persistence, CSS emission, frontend integration, preview, and runtime
  application remain deferred.
