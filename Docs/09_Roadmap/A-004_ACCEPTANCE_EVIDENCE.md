# A-004 Acceptance Evidence

**Checkpoint:** A-004 — Controlled provider selection, endpoint configuration,
and credential handling

**Starting commit:** `eabc19d927a52f771e9dc2580c07b20a3644969d`

**Status:** Accepted locally on 2026-09-01

## Accepted outcome

The desktop now exposes a host-owned two-provider catalog. Offline echo remains
available without settings or network access. The OpenAI Responses provider can
be selected only after its exact bounded settings and credential availability
have been validated.

The settings surface:

- displays only `ups.offline-echo` and `ups.openai-responses`;
- fixes the external endpoint to `https://api.openai.com/v1/responses`;
- bounds model, temperature, and maximum-output-token values;
- accepts an API key only during an explicit save and never displays it again;
- reports only `missing`, `stored`, or `not-required` credential state; and
- requires separate confirmations for credential clearing and execution.

Configured execution recomposes the current durable saved prompt, resolves the
DPAPI-protected credential inside the provider, invokes the existing typed
Provider SDK once, and returns only bounded non-secret output and metadata.

## Persistence and secret boundary

SQLite remains at schema version `1`. Non-secret settings use exact-shape,
atomic `provider-settings.json` under Tauri application data. The fixed opaque
credential reference is safe to persist; its value is not.

On Windows, credential bytes are protected by current-user DPAPI and written to
an application-owned `.dpapi` blob. Installed restart tests prove the settings
and credential availability survive a new process, the JSON document and
ciphertext do not contain the plaintext key, protocol results do not contain it,
and explicit clearing removes the blob.

## Desktop IPC boundary

The fixed allowlist now contains sixteen commands. A-004 adds:

1. `providers.catalog`
2. `providers.settings.save`
3. `providers.credentials.clear`
4. `library.prompts.execute-configured`

The webview cannot supply an arbitrary provider, endpoint, credential reference,
header, option name, final prompt, executable, module, file path, or environment
value. The configured result is limited to 12,500 Unicode characters so the
entire response remains within the 16,384-byte IPC envelope.

## Verification record

The completed implementation passed:

- complete Python and Engineering suite: `917 passed, 1 skipped`;
- required frozen installed-sidecar lifecycle suite: `4 passed`;
- focused A-004/A-003/backend IPC suite: `31 passed`;
- Rust unit tests: `7 passed`;
- strict Rust Clippy across all targets with warnings denied;
- frontend unit tests: `29 passed`;
- frontend production build;
- strict Mypy for the six changed production Python modules;
- Ruff for the changed Python and acceptance-test sources;
- npm dependency audit: zero vulnerabilities;
- Engineering build pipeline: four stages succeeded; and
- a fresh Tauri Windows x64 release build and NSIS package.

The single Python skip is the existing Windows-host symbolic-link availability
case and is not an A-004 regression.

The complete release wrapper passed all validation, audit, sidecar, and
installed-layout stages, then correctly stopped at its clean-working-tree
precondition because these A-004 changes are intentionally uncommitted. The
review installer was therefore produced with the direct repository Tauri build.

## Packaged artifact evidence

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Frozen backend sidecar | 16,457,385 | `000d923e89fdb78e004c4b5de36e1526bc7435b755d507b3133be0db57e13359` |
| Sidecar manifest | 733 | `f7d67aa45cc4c0a2e198fbc378c2ab8bf6343c42c22462e43c915253c649bc74` |
| Windows x64 NSIS installer | 17,935,193 | `45d0f59aeebd4ebaa8565ce337c53610b035b7a1a8767f83f3daf4f0af697da1` |
| Locked sidecar requirements | 1,467 | `46ddffdf4919fb730cacf332867ece62eba3db3b7e53a899e6c6cda85f1b4237` |

The manifest records the same sidecar size and SHA-256, application version
`0.2.0-alpha`, protocol version `1`, target `x86_64-pc-windows-msvc`, Python
`3.12.10`, and PyInstaller `6.22.2`.

## Preserved boundary

A-004 adds no arbitrary provider loading, unrestricted endpoint or option,
model discovery, streaming, cancellation, retry, background execution, history
persistence, workflow UI, import/export, sync, marketplace, telemetry, or
automatic credential validation. The Windows x64 installer remains unsigned.

## Exact next checkpoint

The exact next checkpoint is **A-005 — Workflow authoring, validation, and
bounded sequential execution UI**. It must reuse the schema-1 Workflow SDK,
trusted host operation registry, deterministic planner, and current explicit
provider-execution boundaries without introducing dynamic handlers, retries,
parallelism, background scheduling, or persisted execution state.
