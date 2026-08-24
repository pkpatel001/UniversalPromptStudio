# Application IPC

`Backend.ipc` is the A-001.1 application-owned JSON-lines boundary used by the
Tauri host. It creates one in-memory `ApplicationContainer`, accepts only the
closed `application.readiness` command, and serves until stdin reaches EOF.

Development probe:

```powershell
'{"schema_version":1,"request_id":"manual-1","command":"application.readiness","payload":{}}' |
  python -m Backend.ipc
```

The server writes protocol responses only to stdout. It performs no persistence,
provider request, workflow execution, network access, subprocess launch, or
repository write.

See `Docs/04_Backend/IPC_PROTOCOL.md` for the complete host and trust boundary.

