# ADR-0031: Managed-Theme Integrity and Reversible Lifecycle

**Status:** Accepted  
**Milestone:** E-015.8

## Context

E-015.7 installs one exact external theme manifest with a deterministic
`theme-installation.json` provenance receipt. The receipt was evidence at the
write boundary, but later discovery did not verify it. A modified or incomplete
managed installation could therefore be parsed like ordinary project-authored
theme metadata. Installed themes also had no safe way to leave and re-enter the
active catalog without permanent deletion.

## Decision

### Strict receipt contract

`ThemeInstallationReceiptReader` owns the exact schema-1 JSON receipt. It uses a
bounded UTF-8 read, rejects duplicate JSON keys, requires exact object fields,
and validates canonical theme identity, version, package filename, lowercase
SHA-256 values, manifest size, trust-policy identifier, and the recorded
external-theme acknowledgement. The approved digest must equal the recorded
package digest.

`ThemeManagedThemeVerifier` accepts only an exact managed version directory:

```text
<theme-id>/<version>/
├── theme-manifest.yaml
└── theme-installation.json
```

Both entries must be regular non-symlinked files. The current manifest bytes
must match the receipt size and SHA-256, parse through the strict theme reader,
and agree with both receipt identity and directory identity. Additional files or
directories invalidate the managed installation.

### Catalog admission

Theme discovery distinguishes provenance by host-owned location. Manifests
beneath exact `Themes/Installed/` must pass managed verification before becoming
`ThemeRecord` values. Missing, malformed, inconsistent, or modified receipts and
manifests produce `theme.provenance.invalid` and are excluded. Catalog and
frontend synchronization already fail when discovery reports an issue.

Themes outside the managed directory remain project-authored metadata under the
existing E-015.1 through E-015.3 rules and do not require installation receipts.
This avoids changing the scaffold and built-in authoring contracts.

### Inventory and reversible state

`ThemeManagedThemeService` inventories both active and disabled installations,
verifies every exact version directory, preserves stable ordering, and reports
layout, integrity, root, container, and cross-state duplicate problems.

Disable moves one verified active version atomically from:

```text
Themes/Installed/<theme-id>/<version>/
```

to the reserved discovery-ignored location:

```text
Themes/.ups-theme-disabled/<theme-id>/<version>/
```

Restore performs the exact reverse move. The manifest and receipt bytes are not
rewritten. Both transitions require canonical identity, exact recorded package
SHA-256 approval, explicit action acknowledgement, an absent target, and a ready
non-mutating plan. The executor re-verifies source bytes and plan identity
immediately before `os.replace`.

The CLI exposes:

```powershell
python -m Engineering theme install verify
python -m Engineering theme install disable ID --version VERSION --approve-package-sha256 SHA256 --acknowledge-disable
python -m Engineering theme install disable ID --version VERSION --approve-package-sha256 SHA256 --acknowledge-disable --apply
python -m Engineering theme install restore ID --version VERSION --approve-package-sha256 SHA256 --acknowledge-restore --apply
```

Disable and restore are planning-only unless `--apply` is present.

### Update and frontend behavior

New versions continue to install side by side through E-015.7. There is no
overwrite or implicit version migration. A reviewed older version may be
disabled afterward.

Lifecycle changes do not synchronize the generated frontend catalog, activate a
theme, or rewrite preferences. The existing catalog freshness gate requires a
separate explicit synchronization. Exact preference lookup already falls back to
the default when a selection is absent from the current catalog.

## Security boundary

- Receipt verification proves internal consistency with the recorded installation
  evidence; it is not a signature, MAC, authenticated publisher, or defense
  against a malicious local writer who can replace both manifest and receipt.
- Disabled data is retained and reversible, not securely erased or uninstalled.
- No network, remote repository, marketplace, updater, certificate, trust store,
  revocation service, or automatic repair is introduced.
- No CSS, asset, code, or arbitrary file is loaded or executed.
- Existing targets are never merged or replaced.

## Consequences

- Managed external themes cannot enter a newly compiled catalog with missing or
  inconsistent provenance.
- Operators can inspect exact package and manifest digests before lifecycle
  changes.
- Disable and restore preserve evidence and avoid permanent deletion.
- E-015 now has a complete bounded path from declarative authoring through
  installation, verification, catalog transport, explicit application, and
  reversible managed lifecycle.
- Publisher signatures, permanent uninstall, remote acquisition, assets, live
  preview, and accessibility certification remain future product enhancements.
