# ADR-0030: Controlled External-Theme Installation, Provenance, and Trust

**Status:** Accepted  
**Milestone:** E-015.7

## Context

E-015.1 through E-015.6 established a closed declarative manifest, deterministic
discovery and token compilation, reversible frontend application, and build-time
catalog transport. External themes still need a bounded ingress path. Manifest
validity alone cannot establish where a package came from or authorize its
installation, and installation must not silently become activation.

## Decision

### Canonical data-only package

An external theme package is a ZIP named:

```text
<theme-id>-<theme-version>.ups-theme.zip
```

It contains exactly one root `theme-manifest.yaml`. CSS, scripts, assets, fonts,
icons, URLs, documentation, nested directories, and additional archive members
are not accepted. `ThemePackageInspector` reads one bounded byte snapshot,
rejects symlinked packages and members, encryption, unsupported compression,
oversized archives and manifests, malformed UTF-8 or YAML, and filename/manifest
identity mismatches. The complete package and manifest receive SHA-256 digests;
inspection never extracts the archive.

### Trust policy

Installation requires both an exact caller-supplied package SHA-256 and the
explicit `--acknowledge-external-theme` action. A missing or mismatched digest,
or a missing acknowledgement, blocks readiness. Approval is scoped to the exact
package bytes for this operation.

This is an integrity and consent policy, not publisher authentication. It does
not verify a signature, identity, reputation, ownership, review, accessibility,
or safety claim. No reusable trust-store entry is created.

### Planning and installation

`ThemeInstallationPlanner` combines package inspection and trust assessment with
the existing discovery and Theme SDK compatibility rules. The host derives the
only target:

```text
Themes/Installed/<theme-id>/<theme-version>/
```

The approved theme root must exist and may not be a symlink. Symlinked target
components, existing targets, installed duplicate identities, incompatible SDK
levels, and existing discovery issues block installation. Planning writes
nothing.

`ThemeInstaller` accepts only a ready in-memory plan. It creates a same-volume
staging directory, writes and flushes the exact inspected manifest plus
`theme-installation.json`, then atomically renames the directory into the absent
target. Replacement is never attempted. Failure removes the private staging
directory and leaves no installed target. Discovery reserves and ignores the
`.ups-theme-*` staging prefix, so an in-progress installation is never cataloged.

The deterministic schema-1 receipt records theme identity, caller-provided
source label, package filename, package and manifest digests and sizes, exact
approved digest, acknowledgement, and trust-policy identifier. It omits a clock
timestamp so identical reviewed inputs produce identical receipts. The source
label is provenance supplied by the caller, not an authenticated publisher.

### CLI

```powershell
python -m Engineering theme package inspect PACKAGE
python -m Engineering theme install plan PACKAGE --approve-sha256 SHA256 --acknowledge-external-theme
python -m Engineering theme install apply PACKAGE --approve-sha256 SHA256 --acknowledge-external-theme --source-label LABEL
```

The project `Themes/` directory is the default install root; tests and tooling
may pass an explicit `--root`.

## Security boundary

- Packages remain data-only and are never extracted conventionally.
- Installation never emits CSS, loads assets, executes code, or applies styles.
- Installation does not synchronize the frontend catalog; transport remains a
  separate explicit build-time action.
- No network, download, marketplace, signature, certificate, publisher registry,
  persistent trust grant, update, removal, rollback, or revocation mechanism is
  introduced.
- Existing targets are not replaced or merged.

## Consequences

- Reviewed external theme bytes can now enter a project-local managed root with
  exact integrity evidence and deterministic provenance.
- Installed themes remain inactive until separately transported and explicitly
  selected through the existing E-015.6/E-015.5 boundaries.
- Package signing, authenticated publishers, update/removal workflows,
  accessibility certification, assets, preview, and remote acquisition remain
  future checkpoints.
