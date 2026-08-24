# Engineering Toolkit architecture

**Closure milestone:** E-017.3
**Toolkit status:** Complete for application development
**Product status:** Alpha; user-facing vertical slices remain

## Purpose

The Engineering Toolkit is the repository-owned foundation used to validate,
generate, build, package, and safely integrate Universal Prompt Studio
extensions. It is not the desktop product and it does not grant autonomous
authority to mutate or publish the repository.

## Layered ownership

```text
Application composition roots and presentation adapters
    -> domain SDKs: Plugin, Provider, Theme, Workflow, SelfGeneration
        -> Templates / Artifacts (definitions, variables, manifests)
            -> Code Generation (rendering, paths, conflicts, writes)
    -> shared Engineering services: configuration, validation, diagnostics,
       documentation, build, release, and manifest inventory
```

Domain subsystems own their schemas, semantic validation, compatibility, and
post-generation verification. The Manifest System inventories registered
families and delegates parsing to those owners. Template orchestration resolves
only registered definitions. Code Generation owns destination safety and file
writes. CLI modules are adapters over these services, not alternate domain
implementations.

## Established lifecycle

1. Parse bounded, typed input.
2. Validate semantic and trust constraints without side effects.
3. Discover only explicit roots and preserve provenance.
4. Plan deterministically and expose stable issues.
5. Require explicit host registration or exact-byte approval where runtime
   authority is involved.
6. Execute only a validated plan through the owning service.
7. Record deterministic manifest or provenance evidence.
8. Verify structure, integrity, and drift independently.

Passive inspection never imports extensions, contacts services, reads
credentials, launches subprocesses, or writes files. Trusted plugin and
workflow/provider handlers execute in the host process and are explicitly not a
sandbox.

## Toolkit map

| Area | Owner | Contract |
| --- | --- | --- |
| Paths and configuration | `Engineering.core.paths`, `Engineering.core.config` | Canonical repository paths and typed settings |
| Standards and diagnostics | `Engineering.Standards`, `Engineering.core.diagnostics` | Validation rules and structured environment reports |
| Documentation | `Engineering.Documentation` | Deterministic generated documentation and manifest |
| Rendering and writes | `Engineering.CodeGeneration` | Safe paths, conflicts, dry-run, writes, rollback |
| Template artifacts | `Engineering.Templates` | Definition catalog, variables, execution, artifact manifests |
| Build | `Engineering.BuildSystem` | Deterministic profiles and build manifest |
| Release | `Engineering.ReleaseSystem` | Local inspected packages, checksums, release manifest |
| Manifest inventory | `Engineering.ManifestSystem` | Passive discovery, compatibility, relationships, migration plans |
| Plugins | `Engineering.PluginSystem` | Metadata, catalog, package planning, explicit trusted runtime |
| AI providers | `Engineering.ProviderSystem` | Metadata, catalog, controlled registration and invocation |
| Themes | `Engineering.ThemeSystem` | Declarative tokens, transport, selection, managed lifecycle |
| Workflows | `Engineering.WorkflowSystem` | Declarative DAGs, catalog, planning, bounded sequential execution |
| Self-generation | `Engineering.SelfGeneration` | Allowlisted Engineering scaffold planning, execution, and drift checks |

## Application boundary

`Backend/core/container.py` is the current Python composition root. It registers
the offline provider and workflow reference implementations explicitly. A-001.1
adds one bounded readiness path from the Tauri/Vite frontend to a long-lived
development Python process. The exact schema and process boundary are documented
in `Docs/04_Backend/IPC_PROTOCOL.md`. Release builds fail closed until A-001.2
bundles an explicit sidecar/runtime.

## Change rule after closure

E-017 closes toolkit-first development. Extend the toolkit only when a thin
application slice demonstrates a concrete missing contract. New work should
prefer an end-to-end user outcome over speculative framework expansion.

See also:

- `Docs/09_Roadmap/ENGINEERING_TOOLKIT_CAPABILITY_MATRIX.md`
- `Docs/09_Roadmap/ENGINEERING_TOOLKIT_READINESS.md`
- `Docs/09_Roadmap/APPLICATION_DEVELOPMENT_HANDOFF.md`
- `Docs/023_SECURITY.md`
