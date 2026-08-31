# A-003 Acceptance Evidence

**Checkpoint:** A-003 — Prompt composition and offline reference execution

**Starting commit:** `d59031bc4bc44055671bd929282418610043c1a6`

**Status:** Accepted locally on 2026-08-31

## Accepted outcome

The desktop now turns one durable project-owned prompt into an explicit local
composition and execution flow:

- enabled saved blocks are rendered in stored order through the existing
  `PromptBuilder` and domain block types;
- the final assembled prompt is presented separately from editable saved blocks;
- block edits invalidate any prior preview until the prompt is saved and
  recomposed;
- execution reloads and recomposes durable state rather than trusting arbitrary
  prompt text or a prior webview preview;
- only the host-authored `ups.offline-echo` provider is accepted;
- execution requires explicit confirmation; and
- the bounded result includes only provider identity/version, a correlated UUID,
  output, unit counts, and composed character count.

Composition, output, and execution metadata are ephemeral. SQLite remains at
schema version `1`; no migration or execution-history persistence was added.

## Desktop IPC boundary

The fixed allowlist now contains twelve commands. A-003 adds:

1. `library.prompts.compose`
2. `library.prompts.execute-offline`

Composition accepts only canonical `project_id` and `prompt_id` values. Offline
execution accepts those IDs, the exact provider identity `ups.offline-echo`, and
`confirm: true`. The webview cannot provide final prompt text, provider options,
a model, endpoint, credential, path, environment value, or arbitrary provider.

The A-003 runtime bounds are:

- composed final prompt: 1–12,500 Unicode characters;
- offline result: 1–12,564 Unicode characters;
- enabled/total block counts: consistent with at most 12 saved blocks;
- provider identity/version: exactly `ups.offline-echo` / `1.0.0`; and
- execution identity: one canonical UUID correlated with the provider result.

Rust and the frontend independently revalidate ownership, exact result fields,
text/count bounds, provider identity/version, execution correlation, and safe
errors. Provider failures cross the desktop boundary only as `execution.failed`
with a fixed presentation message.

## Verification record

The completed implementation passed:

- full Python suite against the freshly frozen sidecar: `906 passed, 1 skipped`;
- required frozen-sidecar lifecycle, installed-layout, build, and release checks:
  `10 passed`;
- focused A-003 service/provider/IPC tests: `11 passed`;
- integrated source IPC tests after capability update: `37 passed`;
- Rust unit tests: `6 passed`;
- Rust Clippy across all targets with warnings denied;
- frontend unit tests: `28 passed`;
- frontend production build;
- Mypy across the five changed production Python modules: no issues;
- Ruff across the changed Python sources;
- Engineering build pipeline: four stages succeeded;
- Engineering manifest validation: four valid manifests, zero issues;
- manifest migration planning: one existing documentation plan, one step, zero
  issues; and
- a fresh Tauri Windows x64 release build and NSIS package.

The single Python skip is the existing Windows-host symbolic-link availability
case; it is not an A-003 regression.

## Installed lifecycle evidence

The frozen sidecar test copies the executable into an installed-style directory,
creates and edits a prompt in a separate per-user app-data directory, stops the
process, starts a new process, and then:

1. verifies the saved prompt and local search result;
2. composes the saved enabled block;
3. executes the recomposed prompt through `ups.offline-echo`;
4. validates the bounded result and provider metadata;
5. deletes the prompt and project through existing confirmations; and
6. verifies SQLite remained only under app data.

## Packaged artifact evidence

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Frozen backend sidecar | 16,436,834 | `5554bb3f6e19f74b76f3491a9b7862e4b2fb4a75620a2454e5e89ccace6833d2` |
| Sidecar manifest | 733 | `c3909f2fc6efec86f70858c36533153a1c45acafdf6c54fa78ae913450d628c5` |
| Windows x64 NSIS installer | 17,886,576 | `892b544742bacdf55aebf33fec5a4e436445a73cf0dc6d0de9192439bde21e06` |
| Locked sidecar requirements | 1,467 | `46ddffdf4919fb730cacf332867ece62eba3db3b7e53a899e6c6cda85f1b4237` |

The manifest records the same sidecar size and SHA-256, application version
`0.2.0-alpha`, protocol version `1`, target `x86_64-pc-windows-msvc`, Python
`3.12.10`, and PyInstaller `6.22.2`.

## Preserved boundary

A-003 adds no arbitrary provider loading, external endpoint, credential access,
caller-defined provider options, model discovery, streaming, cancellation,
retry, workflow authoring, background execution, history persistence, network
access, import/export, or sync. The Windows x64 installer remains unsigned.

## Exact next checkpoint

The exact next checkpoint is **A-004 — Controlled provider selection, endpoint
configuration, and credential handling**. It must preserve the offline reference
path and make secret storage, redaction, provider authorization, endpoint bounds,
and option schemas explicit before adding external provider execution.
