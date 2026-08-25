# Desktop-to-Python IPC protocol

**Checkpoint:** A-001.2
**Protocol:** 1
**Current command:** `application.readiness`

## Topology

```text
Vite webview
    -> Tauri custom command: backend_readiness(requestId)
        -> Rust BackendManager
            -> declared sidecar: universal-prompt-studio-backend
                -> ApplicationIpcRouter
                    -> one in-memory ApplicationContainer
```

The webview cannot select an executable, argument, Python module, IPC command,
path, or payload. Rust exposes one custom Tauri command and translates it to one
fixed application command. The webview has no shell-plugin permission.

## Transport

Rust lazily starts one long-lived target-triple sidecar after the first
readiness request. It writes one UTF-8 JSON object per line to stdin and reads
one correlated JSON object per line from stdout. Rust terminates the child when
the manager is dropped or a transport failure invalidates it.

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
    "sidecar_identity": "com.universalpromptstudio.backend",
    "application_version": "0.2.0-alpha",
    "protocol_version": 1,
    "capabilities": ["application.readiness"]
  }
}
```

Rust verifies the exact sidecar identity, Cargo/application version, protocol
version, command capability, response schema, and request correlation before it
returns readiness to the frontend. Python-originated error detail is collapsed
to a fixed Rust-owned unavailable response.

## Lifecycle and recovery

- Startup is lazy and uses Tauri's declared `externalBin` identity.
- Development and release builds use the same frozen executable; there is no
  system-Python or checkout fallback.
- Requests are serialized through one manager lock and reuse one process.
- Responses must arrive within three seconds and match the request ID.
- Transport, timeout, malformed response, or process failures discard the child;
  a later user action starts a fresh process.
- The frontend disables the readiness control while pending and presents only
  bounded ready or unavailable state.
- The frozen Python router creates one application container per process and
  supports multiple requests until stdin closes or Rust terminates the child.

## Build and package boundary

`Scripts/build-sidecar.ps1` installs a SHA-256-locked PyInstaller/runtime set
into an ignored lock-hash-specific environment. It creates
`universal-prompt-studio-backend-$TARGET_TRIPLE.exe`, validates its identity
probe, and writes a checksum manifest. Tauri declares the suffix-free base in
`bundle.externalBin` and includes the generated build manifest as a resource.

The release system independently validates the build manifest and executable,
stages the sidecar as `desktop-sidecar`, checks its PE structure, and records its
size and SHA-256 alongside the unsigned NSIS installer.

## Trust boundary

The sidecar is trusted application code with the user's process authority; this
protocol is not a sandbox. Authority is reduced through exact schemas, one
frontend command, one application command, bounded messages, fixed executable
identity, no caller-selected arguments, minimal inherited Windows environment,
correlation, timeout, checksum coverage, and crash recovery.

Relevant Tauri guidance:

- <https://v2.tauri.app/concept/inter-process-communication/>
- <https://v2.tauri.app/develop/sidecar/>
- <https://v2.tauri.app/security/capabilities/>
- <https://v2.tauri.app/plugin/shell/>
