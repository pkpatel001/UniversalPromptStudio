# Architecture

Universal Prompt Studio follows Clean Architecture. Dependencies point inward:

1. Presentation Layer
2. Application Layer
3. Domain Layer
4. Infrastructure Layer

The UI communicates with application services only. Services use interfaces and repositories. Infrastructure provides replaceable implementations for storage, AI providers, search, plugins, and exports.

## Current Phase

The current scaffold defines:

- Domain models for projects, prompts, prompt blocks, execution requests, and execution results.
- ABC interfaces for provider systems.
- Repository contracts.
- Provider registry.
- Event bus.
- Application services.
- In-memory and dummy implementations for early development.
- Whoosh-backed search adapter behind the `SearchProvider` interface.

## Composition Root

`Backend/core/container.py` is the dependency-injection composition root. Presentation adapters should request services from an application container instead of constructing repositories, providers, validators, or optimizers directly.
