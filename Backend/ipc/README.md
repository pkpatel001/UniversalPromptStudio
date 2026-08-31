# Application IPC

`Backend.ipc` is the application-owned JSON-lines boundary frozen into the
Tauri sidecar. A-003 creates one SQLite `ApplicationContainer` in the fixed
app-data directory supplied by Rust. It serves twelve closed readiness, library,
composition, and offline-execution commands until stdin reaches EOF or Rust terminates it.

Temporary development probe:

```powershell
$env:UPS_APP_DATA_DIR = Join-Path $env:TEMP "ups-ipc-probe"
'{"schema_version":1,"request_id":"manual-1","command":"application.readiness","payload":{}}' |
  python -m Backend.ipc
Remove-Item -LiteralPath $env:UPS_APP_DATA_DIR -Recurse -Force
Remove-Item Env:UPS_APP_DATA_DIR
```

Production does not accept this directory from the webview: Rust resolves
Tauri's application data directory after clearing the child environment. The
server writes protocol responses only to stdout. It performs bounded SQLite
project/prompt management, deterministic saved-block composition, and confirmed
execution through the fixed host-authored `ups.offline-echo` provider. It exposes
no arbitrary provider, option, credential, endpoint, workflow, network access,
arbitrary file access, or subprocess launch.

Future, invalid, and unavailable databases return safe errors and remain
unchanged.

See `Docs/04_Backend/IPC_PROTOCOL.md` for the complete host and trust boundary.

