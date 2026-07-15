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

The repository currently contains:

* Core backend contracts and interfaces
* Abstract Base Classes (ABCs) for extensibility
* Event Bus implementation
* Provider Registry foundation
* Prompt Builder foundation
* Repository abstractions
* SQLite-ready persistence boundaries
* Documentation framework
* Engineering Toolkit foundation
* Automated testing framework
* Minimal Tauri/Vite frontend shell

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

Planned milestones include:

* Documentation Generation Framework
* Advanced Prompt Builder
* Workflow Engine
* Search Engine Enhancements
* Plugin SDK
* AI Provider SDK
* Local LLM Integration
* GitHub Synchronization
* Multi-Agent Workflows
* Marketplace Ecosystem

## Contributing

Contributions, suggestions, issue reports, and pull requests are welcome.

Please follow the project's coding standards and documentation guidelines before submitting changes.

## License

This project is licensed under the Mozilla Public License 2.0 (MPL 2.0).

See the LICENSE file for details.

Copyright (c) 2026 The Patel Brothers Creative Solutions.
