# ADR-0040: Bounded desktop-to-Python IPC foundation

**Status:** Accepted  
**Checkpoint:** A-001.1

## Context

The Tauri/Vite shell and Python application composition root existed without a
production-shaped communication boundary. A generic RPC layer, shell plugin, or
data-selected Python invocation would grant the webview unnecessary authority.
Bundling a Python runtime is also a separate packaging decision that should not
be hidden inside the first protocol checkpoint.

## Decision

Use one Tauri custom command backed by a Rust-owned, long-lived development
Python child process. Rust launches only `python -m Backend.ipc` from the fixed
compile-time repository root. The child speaks strict bounded JSON-lines over
stdin/stdout and owns a closed application router with only
`application.readiness`.

Rust validates request identifiers before launch, serializes requests, requires
protocol/version/shape/correlation agreement, applies a three-second timeout,
and discards a failed child. EOF initiates shutdown and an unresponsive child is
terminated after a bounded wait. The frontend accepts only the exact readiness
result and exposes pending, ready, and unavailable states.

Release builds do not use the development path or system Python. They fail
closed until A-001.2 supplies an explicitly bundled sidecar/runtime.

## Why no shell plugin

Tauri's official sidecar flow requires explicit `externalBin` configuration;
the shell plugin additionally requires spawn/execute permissions and command
scope. A-001.1 has no bundled binary yet, so registering shell authority would
add capability without delivering the packaging boundary. Direct Rust process
ownership keeps the webview surface limited to the custom command.

## Consequences

- The protocol is real and end-to-end in development, including one-process
  reuse and safe restart behavior.
- The first UI action is non-destructive and offline.
- No arbitrary command, path, module, function, or payload crosses the boundary.
- A packaged build presents a bounded unavailable state rather than depending on
  the build machine's checkout.
- A-001.2 must produce and declare the distributable sidecar, then verify the
  installed process lifecycle before prompt features begin.

## Non-goals

- prompt persistence or execution;
- provider, credential, or network access;
- generic RPC/reflection;
- plugin or workflow loading;
- shell-plugin permissions; and
- claiming process isolation or sandboxing.

