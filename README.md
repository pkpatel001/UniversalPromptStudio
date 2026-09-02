# Universal Prompt Studio

Universal Prompt Studio (UPS) is an offline-first, AI-agnostic desktop application for professional prompt engineering, prompt management, workflow design, template creation, and AI provider integration.

The project is designed around Clean Architecture principles, emphasizing modularity, maintainability, extensibility, and long-term sustainability.

## Core Principles

* Offline-first operation
* AI-provider agnostic architecture
* Clean Architecture
* Dependency Injection
* Repository Pattern
* Plugin-based extensibility
* Workflow-driven prompt engineering
* Long-term maintainability
* Professional software engineering standards

## Architecture Overview

Universal Prompt Studio follows a layered architecture:

```text
Presentation Layer
        │
        ▼
Application Layer
        │
        ▼
Domain Layer
        │
        ▼
Infrastructure Layer
```

Key design goals:

1. Presentation communicates only with application services.
2. Application services depend on stable interfaces.
3. Domain models remain independent of external technologies.
4. Infrastructure provides replaceable implementations.
5. Providers, plugins, workflows, and exporters are fully extensible.

## Current Status

The Engineering Toolkit is complete through E-017. The repository contains:

* Backend contracts, services, repositories, events, and a composition root
* SQLite persistence and search adapters behind application interfaces
* Controlled plugin, provider, theme, workflow, and self-generation boundaries
* Deterministic validation, documentation, generation, build, release, and manifests
* Automated Python, frontend, and Rust validation
* A Tauri/Vite prompt workspace with controlled themes, workflows, onboarding, and support controls

The desktop product remains alpha. The completed A-001 through A-007 sequence
provides a usable versioned SQLite
prompt library in Tauri-managed app data, with durable project and prompt
creation, ordered-block editing, category/tag organization, project-scoped local
search, and explicit prompt/project deletion across installed application
restarts. Saved enabled blocks can now be previewed as one deterministic final
prompt and explicitly executed through either the host-authored
`ups.offline-echo` reference path or the bounded `ups.openai-responses` path.
OpenAI settings are exact-shape, its endpoint is fixed, and its API key is
protected for the current Windows user with DPAPI rather than stored in SQLite
or web storage. A-007 completes the planned alpha product sequence with bounded
single-item
import/export, atomic application preferences, first-run onboarding, redacted
diagnostics/support export, managed themes, session-only extension activation,
and bounded sequential workflows.

## Technology Stack

### Backend

* Python 3.12+
* SQLAlchemy 2.x
* SQLite
* Whoosh Search

### Frontend

* Tauri
* Vite
* Vanilla JavaScript
* Tailwind CSS

### Tooling

* Pytest
* Ruff
* Black
* isort
* mypy

## Quick Start

Clone the repository:

```powershell
git clone https://github.com/pkpatel001/UniversalPromptStudio.git
cd UniversalPromptStudio
```

Install development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run tests:

```powershell
python -m pytest
```

Verify compilation:

```powershell
python -m compileall Backend
```

## Documentation

Project documentation is located in:

```text
Docs/
```

Engineering and project tooling are located in:

```text
Engineering/
```

## Roadmap

Engineering Toolkit milestones E-001 through E-017 are complete. Product
development now proceeds through thin application vertical slices:

* Explicit desktop-to-Python IPC
* Prompt-library persistence, editing, organization, and search
* Prompt composition and controlled provider execution
* Workflow authoring and execution UI
* Reviewed prompt/workflow portability and redacted support diagnostics

See `Docs/09_Roadmap/PHASE_ROADMAP.md` for the current sequence and boundaries.

## Contributing

Contributions, suggestions, issue reports, and pull requests are welcome.

Please follow the project's coding standards and documentation guidelines before submitting changes.

## License

This project is licensed under the Mozilla Public License 2.0 (MPL 2.0).

See the LICENSE file for details.

Copyright (c) 2026 The Patel Brothers Creative Solutions.
