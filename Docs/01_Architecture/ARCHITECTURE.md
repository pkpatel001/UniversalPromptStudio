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
- Controlled AI-provider SDK adapters for deterministic offline echo and one
  bounded OpenAI Responses integration registered at the composition root.
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
reference implementation, OpenAI Responses implementation, provider-settings
service, DPAPI secret store, and adapter wiring.

A-004 connects the desktop prompt library and provider settings through
one Tauri-owned, target-triple frozen Python sidecar and strict JSON-lines
protocol. Rust resolves the application data directory and Python owns a
versioned SQLite database there. Development and release builds use the same
declared executable. Rust verifies identity, application/protocol/storage
versions, capabilities, correlation, entity shapes, collection bounds, and
project ownership before returning project, composition, or execution data. The
schema-1 model already owned categories, tags, and ordered blocks, so A-002.2
adds no schema migration. Application services own validated edits,
deterministic project-scoped search, prompt deletion, and transactional SQLite
project deletion with dependent prompts. `SavedPromptRuntimeService` reloads a
project-owned prompt, delegates deterministic enabled-block rendering to the
existing `PromptBuilder`, and invokes the existing execution service only with
one of two host-authorized identities. `ups.offline-echo` remains local and
credential-free. `ups.openai-responses` uses a fixed HTTPS endpoint, bounded
model/temperature/output settings, and one opaque credential reference.
Non-secret settings are atomically persisted beside the database while the API
key is encrypted with current-user Windows DPAPI. SQLite remains schema 1.
Composition and execution remain ephemeral; only source library state,
non-secret provider settings, and protected credential availability are durable.

A-005 composes `WorkflowAuthoringService` over a dedicated atomic definition
repository, the existing `WorkflowOperationRegistry`, `WorkflowPlanner`, and
`WorkflowExecutionService`. The desktop authoring model is the canonical
passive Workflow SDK schema 1 rather than a second graph type. Definitions are
durable below application data; plans, step outputs, final values, and run
metadata are ephemeral.

The host registry exposes only echo, uppercase, and saved-prompt execution.
Workflow nodes carry operation identities and exact port contracts but never
handler code. The saved-prompt handler delegates to `SavedPromptRuntimeService`,
so existing project ownership, provider selection, fixed endpoint/options, and
DPAPI credential resolution remain authoritative. Python validates and plans
the current durable definition, Rust independently validates the transport and
outcome, and the frontend independently validates the public schema before
presentation.

## Engineering Toolkit

See `ENGINEERING_TOOLKIT.md` for subsystem ownership, lifecycle boundaries, and
the post-E-017 rule for application-led toolkit changes.
