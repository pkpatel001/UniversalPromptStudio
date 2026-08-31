# Architecture

Universal Prompt Studio follows Clean Architecture. Dependencies point inward:

1. Presentation Layer
2. Application Layer
3. Domain Layer
4. Infrastructure Layer

The UI communicates with application services only. Services use interfaces and repositories. Infrastructure provides replaceable implementations for storage, AI providers, search, plugins, and exports.

## Application phase

The current repository defines:

- Domain models for projects, prompts, prompt blocks, execution requests, and execution results.
- ABC interfaces for provider systems.
- Repository contracts.
- Provider registry.
- Event bus.
- Application services.
- In-memory and dummy implementations for early development.
- A controlled AI-provider SDK adapter and deterministic offline reference
  provider registered at the composition root.
- Whoosh-backed search adapter behind the `SearchProvider` interface.
- A strict workflow SDK, deterministic planner, bounded sequential runner, and
  offline reference handlers.
- A completed Engineering Toolkit with controlled generation and extension
  trust boundaries.

## Composition Root

`Backend/core/container.py` is the dependency-injection composition root. Presentation adapters should request services from an application container instead of constructing repositories, providers, validators, or optimizers directly.

The provider SDK adapter lives in `Backend/infrastructure/providers/`. The
application service continues to depend only on `Backend.interfaces.AIProvider`;
the composition root owns the concrete SDK registry, execution service, offline
reference implementation, and adapter wiring.

A-002.2 connects the desktop prompt library to this composition root through
one Tauri-owned, target-triple frozen Python sidecar and strict JSON-lines
protocol. Rust resolves the application data directory and Python owns a
versioned SQLite database there. Development and release builds use the same
declared executable. Rust verifies identity, application/protocol/storage
versions, capabilities, correlation, entity shapes, collection bounds, and
project ownership before returning project or prompt data to the webview. The
schema-1 model already owned categories, tags, and ordered blocks, so A-002.2
adds no schema migration. Application services own validated edits,
deterministic project-scoped search, prompt deletion, and transactional SQLite
project deletion with dependent prompts.

## Engineering Toolkit

See `ENGINEERING_TOOLKIT.md` for subsystem ownership, lifecycle boundaries, and
the post-E-017 rule for application-led toolkit changes.
