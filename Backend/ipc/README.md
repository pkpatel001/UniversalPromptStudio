# Application IPC

`Backend.ipc` is the application-owned JSON-lines boundary frozen into the
Tauri sidecar. A-004 creates one application container in the fixed app-data
directory supplied by Rust. It serves sixteen closed readiness, library,
composition, provider-settings, credential, and execution commands until stdin
reaches EOF or Rust terminates it.

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
execution through `ups.offline-echo` or the host-authored OpenAI Responses
integration. Non-secret OpenAI settings are atomic app-data JSON; the API key is
a current-user DPAPI blob and is never returned. The endpoint, credential
reference, and option schema are fixed. The boundary exposes no arbitrary
provider, endpoint, option, header, workflow, file access, or subprocess launch.

Future, invalid, and unavailable databases return safe errors and remain
unchanged.

See `Docs/04_Backend/IPC_PROTOCOL.md` for the complete host and trust boundary.

