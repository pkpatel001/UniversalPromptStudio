# Universal Prompt Studio

Universal Prompt Studio is an offline, AI-agnostic desktop application for professional prompt engineering.

This repository is scaffolded around Clean Architecture:

1. Presentation communicates with application services.
2. Application services depend on stable interfaces.
3. Domain models and rules stay independent.
4. Infrastructure provides replaceable implementations.

The current phase provides the core backend contracts, dummy implementations, an event bus, a registry, a prompt builder, SQLite-ready repository boundaries, documentation, tests, and a minimal Tauri/Vite frontend shell.

## Quick Start

```powershell
python -m compileall Backend
python -m pytest Tests
```

Install development dependencies first if pytest is not available:

```powershell
python -m pip install -e ".[dev]"
```

