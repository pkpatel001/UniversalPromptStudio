# ADR-0045: Controlled provider settings and Windows credential protection

- **Status:** Accepted
- **Date:** 2026-09-01
- **Checkpoint:** A-004

## Context

A-003 could compose and execute durable saved prompts only through the local
`ups.offline-echo` reference provider. A-004 needs one useful external path
without turning provider metadata, the webview, or IPC into arbitrary execution
authority. It also needs durable settings without storing an API key in SQLite,
JSON settings, browser storage, logs, errors, or results.

## Decision

The application composition root explicitly registers exactly two user-facing
providers:

1. `ups.offline-echo` version `1.0.0`, local and credential-free; and
2. `ups.openai-responses` version `1.0.0`, using only
   `https://api.openai.com/v1/responses`.

The OpenAI Responses application schema owns the endpoint, a bounded model
identifier, temperature from `0` through `2`, and maximum output tokens from
`1` through `4096`. There is no discovery or caller-defined option map. The
provider is a host-created implementation registered through the existing
Provider SDK runtime; no manifest entry point or external code is loaded.

Non-secret settings are atomically persisted in exact-shape schema-1
`provider-settings.json` below Tauri's per-user application-data directory.
SQLite remains schema version `1`. The only durable credential locator is the
fixed opaque reference `provider:ups.openai-responses:default`.

On Windows, the API key is encrypted with current-user DPAPI and stored as a
bounded application-owned blob below the app-data `credentials` directory. The
raw value is accepted only by the explicit save command, is never returned, and
is resolved inside the Python provider immediately before an explicitly
confirmed execution. Saving settings rolls back a newly changed credential if
the non-secret settings write fails. Clearing the credential is a separate
confirmed operation.

Rust and the frontend independently validate the two-provider catalog, exact
endpoint and reference, setting bounds, availability state, confirmations,
execution identity/version/model, correlation UUID, usage counts, and output
bounds. Remote transport is one HTTPS POST, with a 30-second network timeout and
35-second host response timeout, no retry, no streaming, and no persisted result.
All provider and transport failures collapse to safe fixed errors.

## Consequences

- Users retain a deterministic offline path and gain one controlled external
  execution path.
- Provider settings and credential availability survive restart, while secrets
  remain outside SQLite and the settings document.
- Windows is the only supported credential-storage and packaged platform.
- The endpoint is deliberately fixed. Supporting another origin, provider,
  authentication scheme, or option requires a new host-owned schema and review.
- DPAPI protects against casual disclosure and binds ciphertext to the current
  Windows user; it does not defend against malicious code already running as
  that user.

## Rejected alternatives

- Arbitrary provider IDs, URLs, headers, models, or option dictionaries from the
  webview.
- Storing API keys in SQLite, JSON, localStorage, environment variables, logs,
  or execution history.
- Dynamic provider loading or treating discovered manifests as authorization.
- Automatic model discovery, credential validation calls, retries, streaming,
  or background execution.
