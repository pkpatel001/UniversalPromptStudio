# ADR-0044: Saved-prompt composition and offline reference execution

**Status:** Accepted

**Checkpoint:** A-003

## Context

A-002.2 completed durable local prompt management, including typed ordered
blocks, but the desktop could not show or run the prompt those blocks produce.
The repository already contained `PromptBuilder`, `PromptExecutionService`, and
the host-authored `ups.offline-echo` provider adapter. A-003 needed to expose a
usable vertical flow without granting the webview arbitrary prompt execution,
provider selection, options, credentials, endpoints, or network authority.

## Decision

Add an application-owned `SavedPromptRuntimeService` and two fixed IPC commands:

- `library.prompts.compose` reloads a prompt through its owning project and
  renders enabled blocks through `PromptBuilder` in stored order.
- `library.prompts.execute-offline` requires the same ownership, the exact
  `ups.offline-echo` identity, and `confirm: true`. It recomposes durable state
  and invokes the existing execution service with no caller-supplied options.

The webview never sends final prompt text for execution. Preview is informative;
execution independently reloads and recomposes the saved prompt. Empty
compositions fail before provider invocation.

Composition returns the saved identity/title, final assembled text, enabled and
total block counts, and Unicode character count. Execution returns only owned
identities, fixed provider identity/version, a correlated execution UUID,
bounded output, input/output units, and composed character count. Rust and the
frontend independently validate exact fields, bounds, ownership, provider
identity, version, and correlation.

The desktop presents editable saved blocks, assembled preview, and offline
result as separate surfaces. Any block edit invalidates the prior preview. The
execute control is enabled only after a successful preview and asks for explicit
confirmation.

Composition and execution data are ephemeral. SQLite remains schema version 1
and stores only the prompt library. Provider failures become the fixed safe
`execution.failed` error; provider-authored detail and exceptions do not cross
the Rust boundary.

## Consequences

Positive:

- The first prompt runtime is useful, deterministic, offline, and testable.
- Executed text always derives from project-owned durable state.
- Existing domain, provider, and persistence contracts are reused without a
  schema migration.
- The provider and payload allowlists remain closed across frontend, Rust, and
  Python.
- Frozen-sidecar and installed-layout tests can prove the same flow shipped to
  users.

Tradeoffs:

- Unsaved editor changes cannot be previewed; users must save first.
- Only `ups.offline-echo` can execute and it accepts no model or options.
- Results and execution metadata disappear when the view or process closes.
- There is no streaming, cancellation, retry, or execution history.

## Deferred

A-003 does not authorize external providers, arbitrary provider loading,
endpoint or model discovery, credentials, caller-defined options, network
access, streaming, cancellation, retries, workflows, background execution,
history persistence, import/export, or sync.

Controlled provider selection, endpoint configuration, and credential handling
begin in A-004 and must preserve the offline reference path plus explicit secret
storage and redaction boundaries.
