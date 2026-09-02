# A-008 Acceptance Evidence

**Checkpoint:** A-008 — Beginner-friendly user guide and in-app help

**Starting commit:** `1f056dee79eaa8d5ff5038c0c3069af6496c7397`

**Status:** Accepted locally on 2026-09-02

## Accepted outcome

The approved A-001 through A-008 alpha desktop sequence is complete. The main
workspace now exposes **Help** as a native modal learning surface with 15 fixed,
host-authored topics. Users can search by task, select a topic, follow bounded
steps, read tips, and move among related topics without leaving the application.

Contextual **How this works**, **Block guide**, **Run guide**, workflow,
customization, portability, and settings/support actions open the relevant topic
directly. The dialog follows the existing semantic theme tokens, native focus
and Escape behavior, live-region result feedback, and responsive layout.

The comprehensive `Docs/05_Frontend/USER_GUIDE.md` covers Windows installation,
first launch, a ten-minute quick start, all 12 supported prompt block types,
library organization, offline and OpenAI provider execution, workflows,
portability, themes and full-trust extensions, settings, diagnostics, prompt
recipes, stress testing, troubleshooting, privacy, limitations, and a glossary.

## Help-content and search boundary

The catalog is fixed JavaScript data, frozen after validation-oriented
construction, and identified by unique bounded topic ids. Every related-topic
reference resolves to another authored item. Search is deterministic,
case-insensitive, accent-insensitive, and local; every entered term must occur in
the authored title, category, summary, outcome, prerequisites, steps, tips, or
keywords.

The renderer creates user-visible catalog text with DOM text nodes. It does not
render catalog HTML, inspect user prompts, query application data, read files,
send network requests, or persist search text. The Help UI adds no provider,
workflow operation, extension contribution, or executable content path.

## Preserved desktop boundary

A-008 changes frontend and documentation only. It adds:

- no Python or Rust production implementation;
- no Tauri command or permission;
- no IPC command, payload, or error code;
- no protocol, SQLite, workflow, settings, or portable schema version;
- no network endpoint, filesystem access, picker, shell access, or web storage;
- no background work, telemetry, cloud sync, automatic update, or marketplace;
  and
- no extension installation, permission, persistence, or activation authority.

The desktop remains at protocol version 1, SQLite schema 1, workflow schema 1,
application-settings schema 1, the 16 KiB IPC boundary, and 37 exact commands.

## Verification record

The completed implementation passed:

- complete Python and Engineering suite with frozen-sidecar tests required:
  `945 passed, 1 skipped`;
- Rust unit tests: `13 passed`;
- strict Rust Clippy across all targets with warnings denied;
- Rust formatting check;
- frontend unit tests: `47 passed`, including five Help catalog/search tests;
- frontend production build with `23` transformed modules;
- npm production dependency audit: zero vulnerabilities;
- Engineering build pipeline: four stages succeeded; and
- a fresh Tauri Windows x64 release build and current-user NSIS package.

The single Python skip is the existing Windows-host symbolic-link availability
case and is not an A-008 regression.

Computer-use visual automation was attempted against the local frontend. The
trusted browser-control Node runtime reset twice before it could create the
preview tab, so no automated screenshot or interaction evidence was available.
This host limitation does not replace or invalidate the deterministic catalog
tests, safe renderer construction, frontend production compilation, native
dialog semantics, Rust validation, complete Python suite, or release packaging.

## Packaged artifact evidence

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Frozen backend sidecar | 16,584,624 | `6528fd3539cd0f1e35833149e675934ea5e4a12b345c2810da90538f76c39bc1` |
| Sidecar manifest | 733 | `690541a4e7fb467cc6e2360cc7b0a608d1a684d91de7be73a49b6d53f460dbf3` |
| Windows x64 NSIS installer | 18,264,150 | `84128a0ee9c58a91ff1f21c147d7b166c497fa3fff277a3e2961d8f1418b2a7c` |
| Locked sidecar requirements | 1,467 | `46ddffdf4919fb730cacf332867ece62eba3db3b7e53a899e6c6cda85f1b4237` |

The sidecar and lock artifacts remain deterministic and match the A-007 hashes.
The manifest records the same sidecar size and SHA-256, application version
`0.2.0-alpha`, protocol version `1`, target `x86_64-pc-windows-msvc`, Python
`3.12.10`, and PyInstaller `6.22.2`. Authenticode status for the fresh installer
is `NotSigned`, matching the documented alpha distribution boundary.

## Preserved limitations

Help is English-only, static, and offline. It has no screenshots, remote content
updates, interactive walkthrough automation, access to user content, or
content-specific diagnostic capability. A-008 adds no bulk backup/recovery,
localization, updater, signing, publishing, cloud collaboration, provider
discovery, or advanced workflow behavior.

## Continuation boundary

No A-009 checkpoint is approved. Further development requires a new explicit
product outcome and must preserve the completed A-001 through A-008 storage,
provider, workflow, theme, extension, portability, diagnostics, distribution,
and help-content trust boundaries.
