# Developer onboarding

## Prerequisites

- Python 3.12+
- Node.js and npm versions accepted by `Frontend/package.json`
- Stable Rust toolchain matching `Frontend/src-tauri/rust-toolchain.toml`
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
python -m ruff check Backend Engineering Tests
python -m mypy Backend Engineering
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
cargo check --locked
```

## Architecture entry points

- `Backend/core/container.py` — application composition root.
- `Frontend/src/main.js` — current webview shell.
- `Frontend/src-tauri/src/lib.rs` — current Tauri host.
- `Docs/01_Architecture/ENGINEERING_TOOLKIT.md` — toolkit ownership.
- `Docs/09_Roadmap/APPLICATION_DEVELOPMENT_HANDOFF.md` — next product slice.

CLI adapters live under `Engineering/cli/commands`; domain behavior belongs in
the owning subsystem. Preserve deterministic ordering, explicit roots,
no-overwrite defaults, passive inspection, and documented trust boundaries.

Do not commit generated `build/`, `release/`, `dist/`, cache, or Rust `target/`
output. Do not commit or push unless the current task explicitly requests it.

