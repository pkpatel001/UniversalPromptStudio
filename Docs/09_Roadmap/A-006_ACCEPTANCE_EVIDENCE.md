# A-006 Acceptance Evidence

**Checkpoint:** A-006 — Theme and managed extension lifecycle UI at supported
trust boundaries

**Starting commit:** `10278e6450f687a387a5dd007bf8bf31bb08f09f`

**Status:** Accepted locally on 2026-09-02

## Accepted outcome

The desktop now includes a Customize surface beside the prompt library and
workflow studio. Users can preview, apply, revert, and explicitly remember the
three built-in themes plus compatible managed themes admitted by the host.
Managed theme and extension cards present origin, compatibility, trust state,
exact digest, lifecycle state, and restart behavior before an action is
confirmed.

Theme packages enter only through the fixed application-data inbox. Install
requires the canonical package filename, exact inspected SHA-256, a separate
external-package acknowledgement, and confirmation. Installed themes can be
disabled and restored through the Engineering lifecycle holding area only when
their current package digest still matches the approved digest. The reserved
`ups.*` namespace cannot be installed externally. Any managed-theme integrity
failure closes the dynamic theme catalog rather than exposing a partial set.

Permissionless project-local extensions may be activated only from the fixed
application-data extension root after exact directory-digest verification,
explicit full-trust acknowledgement, and confirmation. Permission-requesting
plugins are blocked before activation. Approval is session-only: every fresh
sidecar starts extensions inactive. A-006 adds no extension installation,
removal, update, persistent approval, permission grant, or dynamic command.

## Persistence and trust boundary

The host derives all customization locations below Tauri application data:

- `theme-packages/` for the bounded managed ingress inbox;
- `themes/` for active themes, managed receipts, and reversible disabled
  packages; and
- `extensions/` for discovered project-local extension directories.

The webview supplies no path, executable, module, command, root, environment
value, CSS, asset, URL, or permission. Theme receipts and disabled state persist
across restart. Extension runtime approval and contributions do not. Existing
schema-1 SQLite, provider settings, DPAPI credential storage, and workflow
definitions remain unchanged.

## Desktop IPC boundary

The fixed allowlist now contains 29 commands. A-006 adds:

1. `customizations.catalog`
2. `themes.install`
3. `themes.lifecycle`
4. `extensions.activate`
5. `extensions.deactivate`

Frontend, Rust, and Python independently enforce exact catalogs, semantic
tokens, canonical identities, stable numeric versions, SHA-256 digests,
bounded issue lists, lifecycle actions, acknowledgements, confirmations, and
safe failures. Catalogs are bounded to 20 themes, 20 extensions, and 10 issues.

## Verification record

The completed implementation passed:

- complete Python and Engineering suite with required sidecar tests: `932 passed,
  1 skipped`;
- required frozen installed-sidecar lifecycle suite: `5 passed`;
- focused A-006/backend IPC suite: `22 passed`;
- Rust unit tests: `11 passed`;
- strict Rust Clippy for the library with warnings denied;
- Rust formatting check;
- frontend unit tests: `36 passed`;
- frontend production build with 17 transformed modules;
- strict Mypy for the changed production Python boundary;
- Ruff for changed Python and acceptance-test sources;
- npm production dependency audit: zero vulnerabilities;
- Engineering build pipeline: four stages succeeded; and
- a fresh Tauri Windows x64 release build and NSIS package.

The single Python skip is the existing Windows-host symbolic-link availability
case and is not an A-006 regression.

Browser visual automation was attempted against the local production surface, but
the host browser helper could not start because its Windows sandbox failed to
apply deny-read ACLs. This environment limitation did not affect compilation,
packaging, protocol, restart, or installed-layout tests.

## Packaged artifact evidence

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Frozen backend sidecar | 16,566,534 | `677e9baaf4dbf2cefec5b8cb4040253af0d87385bff18eabf7b74b6d0e2fe675` |
| Sidecar manifest | 733 | `d6dbbf2043dfc64ab60fa71a2d85f521bd686d4c55b741f0b5666e88ff460e7b` |
| Windows x64 NSIS installer | 18,172,853 | `24c73eef8a08e1e3f0cf646ed69ae02a8a8e6b83fd479034167e3f127aaf12fc` |
| Locked sidecar requirements | 1,467 | `46ddffdf4919fb730cacf332867ece62eba3db3b7e53a899e6c6cda85f1b4237` |

The manifest records the same sidecar size and SHA-256, application version
`0.2.0-alpha`, protocol version `1`, target `x86_64-pc-windows-msvc`, Python
`3.12.10`, and PyInstaller `6.22.2`.

## Preserved boundary

A-006 adds no marketplace, remote discovery, automatic download/update,
publisher trust, signature infrastructure, arbitrary CSS/assets, arbitrary
plugin permissions, dynamic commands, plugin-supplied workflow operations,
webview filesystem authority, persistent extension approval, or silent
activation. The Windows x64 installer remains unsigned.

## Exact next checkpoint

The exact next checkpoint is **A-007 — Import/export, settings, diagnostics,
onboarding, and distribution polish**. It must preserve the completed A-001
through A-006 desktop, storage, provider, workflow, theme, and extension trust
boundaries.
