# ADR-0003 — Code Generation Framework

**Date:** 2026-08-09
**Status:** Accepted
**Milestone:** E-008

## Context

The Engineering Toolkit must eventually produce project artifacts (plugins, providers, themes, workflows) through a controlled, deterministic pipeline rather than ad-hoc `Path.write_text()` calls scattered across the codebase. E-008 establishes the framework that all future generators will consume.

## Decisions

### 1. Package location: `Engineering/CodeGeneration/`

**Chosen:** A top-level subsystem package under `Engineering/`, consistent with the established pattern (`Documentation/`, `Standards/`, `cli/`).

**Rationale:** Each Engineering Toolkit subsystem occupies its own package. Placing CodeGeneration at the same level preserves consistent architecture.

### 2. Template engine: Jinja2 behind abstraction

**Chosen:** Use Jinja2 (already a project dependency in `pyproject.toml`) encapsulated behind a `TemplateRenderer` abstraction.

**Rationale:** Jinja2 provides a proven, expressive template engine. The `SandboxedEnvironment` class is available for safety. The abstraction layer (`TemplateRenderer.render()`) isolates downstream code from Jinja2 internals, preserving future replaceability.

### 3. Plan-before-write architecture

**Chosen:** All generation passes through `GenerationPlan → Validation → Execution → Report`.

**Rationale:** Validates the entire plan before writing any artifact. Preflight failures abort without filesystem writes. Conflict detection occurs before writes. This prevents partial-generation problems.

### 4. Default overwrite policy: NEVER

**Chosen:** Artifacts that would overwrite files with differing content are reported as CONFLICT and not written. An explicit `OverwritePolicy.ALLOWED` opt-in exists for callers that require it.

**Rationale:** The Engineering Toolkit is eventually intended to generate its own source code. Silent overwrite would be destructive. Safe defaults are critical.

### 5. Dependency direction

**Chosen:** `CodeGeneration` depends on `core/` infrastructure (`paths`, `filesystem`, `exceptions`, `validation`). `core/` never depends on `CodeGeneration`.

**Rationale:** Core infrastructure must remain independent of high-level generation functionality. This prevents circular dependencies and preserves testability.

### 6. E-004 validation reuse

**Chosen:** Plan validation uses `ValidationIssue` and `ValidationReport` from `core.validation` rather than a parallel issue model.

**Rationale:** Duplicating the issue/severity model creates maintenance burden and inconsistencies.

### 7. Secret protection

**Chosen:** The engine validates generation context values at preflight, rejecting values whose keys match known sensitive patterns (`api_key`, `token`, `password`, `secret`, `credential`, `private_key`, `access_key`, `auth`) when the value is non-empty.

**Rationale:** Prevents accidental serialization of secrets into generated artifacts. Generators requiring those key names for configuration templates must use placeholder values.

### 8. No configuration file additions in E-008

**Chosen:** Generation policies are explicit per `GenerationRequest`, not loaded from YAML config.

**Rationale:** Prevents premature config schema growth. Config integration is deferred until actual requirements emerge.

### 9. Filesystem integration via `core/filesystem.py`

**Chosen:** All file writes use `filesystem.write_text()`. No new `open()` or `Path.write_text()` abstractions.

**Rationale:** Single filesystem abstraction maintained throughout the toolkit.

### 10. No specialized generators in E-008

**Chosen:** E-008 implements the framework only. Plugin, provider, theme, and workflow generators are deferred to E-009+.

**Rationale:** Framework validation requires working end-to-end pipeline but not every possible generator.

## Consequences

- Future generators (E-009+) implement `Generator.plan()` and delegate to `GenerationEngine`.
- Template files are stored under `Engineering/Templates/CodeGeneration/` using `.j2` extension.
- The existing CLI `generate` placeholder remains unchanged.
- The test suite serves as the end-to-end demonstration of the framework.
