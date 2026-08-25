# Developer onboarding

## Prerequisites

- Python 3.12+
- Node.js and npm versions accepted by `Frontend/package.json`
- Stable Rust toolchain matching the repository-root `rust-toolchain.toml`
- Windows desktop packaging prerequisites only when building NSIS output

Install Python development dependencies and locked frontend dependencies only
when explicitly preparing a development environment:

```powershell
python -m pip install -e ".[dev]"
npm ci --prefix Frontend
```

## Core validation

From the repository root:

```powershell
python -m pytest -q
python -m Engineering manifest validate
python -m Engineering manifest migrations
python -m Engineering theme sync-frontend --root Themes --check
```

From `Frontend`:

```powershell
npm test
npm run build
```

From `Frontend/src-tauri`:

```powershell
cargo test --locked
cargo check --release --locked
```

## Development IPC probe

Run the desktop development host from `Frontend`:

```powershell
npm run tauri dev
```

Select **Check backend**. The Rust host starts the declared target-triple
`universal-prompt-studio-backend` sidecar and reports readiness only after exact
identity, application-version, protocol-version, capability, and correlation
validation. Development and release builds use the same frozen executable.

Build and validate the frozen sidecar from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Scripts/build-sidecar.ps1
$env:UPS_REQUIRE_SIDECAR_TESTS = "1"
python -m pytest -q Tests/test_ipc.py Tests/test_sidecar_build.py Tests/test_sidecar_lifecycle.py
```

Generated sidecar executables and build manifests remain ignored. Tauri builds
invoke the same locked build script automatically.

## Architecture entry points

- `Backend/core/container.py` — application composition root.
- `Backend/ipc/` — application-owned protocol and command router.
- `Frontend/src/backend-client.js` — strict webview readiness client.
- `Frontend/src-tauri/src/backend.rs` — process lifecycle and correlation.
- `Docs/04_Backend/IPC_PROTOCOL.md` — IPC and trust boundary.
- `Docs/09_Roadmap/APPLICATION_DEVELOPMENT_HANDOFF.md` — next product slice.

Do not commit generated `build/`, `release/`, `dist/`, cache, Python bytecode, or
Rust `target/` output. Do not commit or push unless the current task explicitly
requests it.

