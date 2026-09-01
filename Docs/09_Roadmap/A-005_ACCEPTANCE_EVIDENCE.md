# A-005 Acceptance Evidence

**Checkpoint:** A-005 — Workflow authoring, validation, and bounded sequential
execution UI

**Starting commit:** `f946ad719f6dcaa23b9b314a9884c87a26e3b485`

**Status:** Accepted locally on 2026-09-01

## Accepted outcome

The desktop now includes a schema-1 workflow studio beside the existing prompt
library. A user can create, select, edit, save, delete, validate, and explicitly
run a bounded sequential workflow. The authoring surface covers workflow
identity, typed boundary ports, trusted operation nodes, directed edges, runtime
inputs, deterministic planning feedback, step progress, intermediate outputs,
and final outputs.

Operation choices come only from the host-owned registry:

1. `ups.echo-text`
2. `ups.execute-saved-prompt`
3. `ups.uppercase-text`

The saved-prompt operation reuses the current prompt-library and provider
services. It accepts project, prompt, and provider identities but no prompt
text, endpoint, option, or credential. Both offline echo and the configured
OpenAI path remain behind their existing authorization and credential
boundaries.

## Persistence and graph boundary

Workflow definitions use the passive Workflow SDK schema 1. Up to 50
definitions are stored in exact-shape atomic `workflow-definitions.json` below
Tauri application data, beside but separate from schema-1 SQLite. Each desktop
definition is limited to 12,000 encoded bytes, eight boundary ports per side,
eight trusted nodes, and 64 edges.

Structurally valid drafts may be saved before their graph is executable. The
deterministic planner reports missing connections, incompatible types,
duplicate targets, cycles, and other graph failures. Execution remains disabled
until a current saved definition produces a valid plan and the user confirms
the run.

Runtime values retain the Workflow SDK value types and add the tighter desktop
limits of 1,000 characters per string and 6,000 encoded bytes per value. Runs
are sequential and ephemeral. The application stores neither execution history
nor intermediate/final values.

## Desktop IPC boundary

The fixed allowlist now contains 24 commands. A-005 adds:

1. `workflows.operations.list`
2. `workflows.list`
3. `workflows.create`
4. `workflows.get`
5. `workflows.update`
6. `workflows.delete`
7. `workflows.plan`
8. `workflows.execute`

Frontend, Rust, and Python independently enforce exact workflow, operation,
plan, execution, runtime-value, confirmation, and safe-error shapes. The
webview cannot choose a handler implementation, arbitrary operation ID,
executable, module, path, environment value, sidecar command, provider
endpoint, credential reference, or unbounded payload.

## Verification record

The completed implementation passed:

- complete Python and Engineering suite with required sidecar tests: `923 passed,
  1 skipped`;
- required frozen installed-sidecar lifecycle suite: `4 passed`;
- focused A-005/workflow/backend IPC suite: `24 passed`;
- Rust unit tests: `9 passed`;
- strict Rust Clippy across all targets with warnings denied;
- Rust formatting check;
- frontend unit tests: `32 passed`;
- frontend production build;
- strict Mypy for the three new production Python modules;
- Ruff for changed Python and acceptance-test sources;
- npm dependency audit: zero vulnerabilities;
- Engineering build pipeline: four stages succeeded; and
- a fresh Tauri Windows x64 release build and NSIS package.

The single Python skip is the existing Windows-host symbolic-link availability
case and is not an A-005 regression.

Browser and native-app visual automation were attempted after the production
build but the host's automation helper could not start because its Windows
sandbox failed to apply deny-read ACLs. This is a tooling limitation; it did not
affect compilation, packaging, protocol, restart, or installed-layout tests.

## Packaged artifact evidence

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Frozen backend sidecar | 16,480,869 | `cea20e1c3725df9c2961ea0f4418d5dd9f5a1db93060a2a143751468734bc4c2` |
| Sidecar manifest | 733 | `636f8f02ad5dd931b855bca91abd17feb1f89ff149c13a22a2ad54be2adf8cd2` |
| Windows x64 NSIS installer | 18,043,097 | `3903b96da85b055449888a0ec0ed3bc0763726a0c06399053b1b977c49cfa49a` |
| Locked sidecar requirements | 1,467 | `46ddffdf4919fb730cacf332867ece62eba3db3b7e53a899e6c6cda85f1b4237` |

The manifest records the same sidecar size and SHA-256, application version
`0.2.0-alpha`, protocol version `1`, target `x86_64-pc-windows-msvc`, Python
`3.12.10`, and PyInstaller `6.22.2`.

## Preserved boundary

A-005 adds no dynamic handlers, arbitrary operations, plugin-supplied runtime
operations, cycles, conditions, parallelism, retries, cancellation, background
scheduling, resume, execution history, import/export, sync, remote triggers, or
credential transport. The Windows x64 installer remains unsigned.

## Exact next checkpoint

The exact next checkpoint is **A-006 — Theme and managed extension lifecycle UI
at supported trust boundaries**. It must preserve the completed A-001 through
A-005 desktop, storage, provider, and workflow boundaries.
