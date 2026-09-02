# A-007 Acceptance Evidence

**Checkpoint:** A-007 — Import/export, settings, diagnostics, onboarding, and
distribution polish

**Starting commit:** `8752774eb2794b7533acbff86ec5bdaad6260b40`

**Status:** Accepted locally on 2026-09-02

## Accepted outcome

The planned A-001 through A-007 alpha desktop sequence is complete. The main
window now includes a **Settings & support** surface for atomic non-secret
preferences, selected prompt/workflow portability, content-free diagnostics,
and reviewed support export. First-run onboarding explains project ownership,
explicit execution, portable-file review, disabled telemetry, and the absence
of automatic updates.

Compact layout and reduced motion are applied through semantic application
styles and persist in exact-shape schema-1 `application-settings.json` below
Tauri per-user application data. The settings document contains only three
booleans and is atomically replaced. Invalid settings fail unchanged.

## Portable-item boundary

One canonical JSON document carries exactly one prompt or one workflow. It is
limited to 10,000 Unicode characters and remains inside the existing 16 KiB IPC
boundary. The browser-native file picker and Blob download path give the user
ingress/egress without granting the webview Tauri filesystem or shell authority.

Every import is fully validated and previewed before durable change. The preview
reports item identity, title, target, character count, conflict state, allowed
create/replace/skip actions, and SHA-256. Apply requires the same document,
digest, explicit allowed action, review acknowledgement in the UI, and
confirmation. A prompt identity belonging to another project can only be
skipped; it is never moved or replaced silently.

Portable files exclude credentials, execution history, extension approval,
project names, and paths. Provider settings, credential blobs, theme trust
receipts, and extension runtime approval are not portable.

## Diagnostics and support boundary

Diagnostics expose only application/package state, library/workflow counts,
provider availability and credential state, customization counts, and the three
non-secret preferences. Support preview lists included sections and the complete
fixed redaction set before export. The final export is bound to the preview
digest and requires redaction acknowledgement plus confirmation.

Support data excludes credentials, prompt titles/content, workflow definitions
and runtime values, filesystem paths, environment values, extension code, and
contributions. Source and frozen-process tests assert that private prompt text
and application-data paths do not appear.

## Desktop IPC boundary

The fixed allowlist now contains 37 commands. A-007 adds:

1. `application.settings.get`
2. `application.settings.save`
3. `portability.export`
4. `portability.preview`
5. `portability.import`
6. `diagnostics.snapshot`
7. `diagnostics.support.preview`
8. `diagnostics.support.export`

Python enforces domain/storage semantics. Rust independently validates exact
settings policy, identities, targets, documents, filenames, counts, diagnostic
shapes, redactions, digests, actions, acknowledgements, confirmations, and
results. JavaScript validates the presentation contract again before rendering
or downloading it. Safe `product.unavailable` failures cross the bridge; Python
exception detail does not.

## Verification record

The completed implementation passed:

- complete Python and Engineering suite with frozen-sidecar tests required:
  `945 passed, 1 skipped`;
- frozen installed-sidecar lifecycle suite through A-007: `6 passed`;
- focused A-007 Python service/IPC boundary suite: `12 passed`;
- strict Mypy for the changed production Python boundary and focused source
  tests;
- scoped Ruff for all changed Python and acceptance sources;
- Rust unit tests: `13 passed`;
- strict Rust Clippy across all targets with warnings denied;
- Rust formatting check;
- frontend unit tests: `42 passed`;
- frontend production build with 20 transformed modules;
- npm production dependency audit: zero vulnerabilities;
- Engineering build pipeline: four stages succeeded; and
- a fresh Tauri Windows x64 release build and current-user NSIS package.

The single Python skip is the existing Windows-host symbolic-link availability
case and is not an A-007 regression.

Browser visual automation was attempted against the local app surface. The
browser runtime could not start because this host's Windows sandbox helper
failed while applying deny-read ACLs. This environment limitation did not
affect frontend compilation, native dialog semantics, protocol validation,
frozen-process tests, or release packaging.

## Packaged artifact evidence

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Frozen backend sidecar | 16,584,624 | `6528fd3539cd0f1e35833149e675934ea5e4a12b345c2810da90538f76c39bc1` |
| Sidecar manifest | 733 | `690541a4e7fb467cc6e2360cc7b0a608d1a684d91de7be73a49b6d53f460dbf3` |
| Windows x64 NSIS installer | 18,256,357 | `3e06ce0245ab4023b35cfa0dad78eaf80441625d28cc2826886c5551c6581489` |
| Locked sidecar requirements | 1,467 | `46ddffdf4919fb730cacf332867ece62eba3db3b7e53a899e6c6cda85f1b4237` |

The manifest records the same sidecar size and SHA-256, application version
`0.2.0-alpha`, protocol version `1`, target `x86_64-pc-windows-msvc`, Python
`3.12.10`, and PyInstaller `6.22.2`. Authenticode status for the installer is
`NotSigned`, matching the documented distribution boundary.

## Preserved boundary

A-007 adds no bulk backup/restore, arbitrary archive or destination path, cloud
sync, telemetry, automatic upload/update, localization beyond fixed English,
credential export, execution-history persistence, silent conflict resolution,
remote marketplace/discovery, persistent extension approval, installer signing,
publishing, tag, release, commit, or push.

## Continuation boundary

No A-008 checkpoint is approved. Further development requires a new explicit
product outcome and must preserve the completed A-001 through A-007 storage,
provider, workflow, theme, extension, portability, diagnostics, and distribution
trust boundaries.
