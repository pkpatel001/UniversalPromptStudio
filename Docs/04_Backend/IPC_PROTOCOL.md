# Desktop-to-Python IPC protocol

**Checkpoint:** A-001.1  
**Protocol:** 1  
**Current command:** `application.readiness`

## Topology

```text
Vite webview
    -> Tauri custom command: backend_readiness(requestId)
        -> Rust BackendManager
            -> fixed development process: python -m Backend.ipc
                -> ApplicationIpcRouter
                    -> one in-memory ApplicationContainer
```

The webview cannot select an executable, argument, Python module, IPC command,
path, or payload. Rust exposes one custom Tauri command and translates it to one
fixed application command.

## Transport

Rust owns one long-lived child process after the first readiness request. It
writes one UTF-8 JSON object per line to stdin and reads one correlated JSON
object per line from stdout. Standard input EOF is the graceful shutdown signal;
Rust waits briefly, then terminates a child that does not exit.

Messages are limited to 16,384 bytes. Requests and responses reject unknown or
duplicate fields, invalid UTF-8/JSON, non-finite numbers, unsupported protocol
versions, malformed identifiers, and uncorrelated responses.

Request schema:

```json
{
  "schema_version": 1,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "command": "application.readiness",
  "payload": {}
}
```

Success schema:

```json
{
  "schema_version": 1,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "ok": true,
  "result": {
    "status": "ready",
    "application_version": "0.2.0-alpha",
    "protocol_version": 1,
    "capabilities": ["application.readiness"]
  }
}
```

Failures contain `ok: false` and one bounded `error` object with a stable code
and safe message. Raw exceptions, paths, environment values, stderr, and
tracebacks never cross the boundary.

## Lifecycle and failure behavior

- Startup is lazy and occurs on the first readiness request.
- Requests are serialized through one manager lock.
- Responses must arrive within three seconds and match the request ID.
- Transport, timeout, malformed response, or process failures discard the child;
  a later user action may start a fresh process.
- The frontend disables the readiness control while pending and presents only
  bounded ready or unavailable state.
- The Python router creates one application container per process and supports
  multiple requests until stdin closes.

## Development and packaging boundary

Debug builds use the fixed command `python -m Backend.ipc` from the compile-time
repository root. No shell string is constructed and no caller data becomes an
argument. `PYTHONDONTWRITEBYTECODE`, UTF-8, and unbuffered output are fixed by
the host.

Release builds fail closed with `backend.unavailable`. A-001.1 does not pretend
that a system Python or the development checkout is a distributable backend.
The exact next checkpoint, A-001.2, will bundle an explicitly declared Python
sidecar/runtime and verify installed lifecycle behavior.

## Trust boundary

The Python process is trusted application code with the user's process
authority; this protocol is not a sandbox. The protection is reduction of
authority: exact schemas, one Tauri command, one application command, bounded
messages, fixed launch arguments, correlation, timeout, and fail-closed release
behavior.

Relevant current Tauri guidance:

- <https://v2.tauri.app/concept/inter-process-communication/>
- <https://v2.tauri.app/develop/sidecar/>
- <https://v2.tauri.app/security/capabilities/>
- <https://v2.tauri.app/plugin/shell/>

