# ADR-0004 — Template and Artifact System

**Date:** 2026-08-16
**Status:** Accepted
**Milestone:** E-009

## Context

E-008 established how UPS safely plans, renders, and writes generated files.
Later generators also need a reusable description of which templates exist,
which inputs they accept, which artifacts they produce, and how generated
output can be verified. Building a second renderer or generation engine would
split policy and undermine the E-008 safety guarantees.

## Decisions

### 1. E-009 extends E-008

E-009 owns template definitions, discovery, metadata, variables, catalogs,
artifact manifests, and controlled execution. E-008 continues to own source
template resolution, rendering, planning, path safety, conflicts, writes, and
generation reports.

### 2. Definitions are immutable and versioned

Definitions use frozen domain models with stable dot-separated identifiers and
semantic versions. Multiple versions may coexist; an omitted version resolves
to the highest semantic version.

### 3. File-backed definitions use YAML

Bundled definitions use the deterministic `*.template.yaml` convention. YAML
contains metadata, declared variables, and artifact definitions. Discovery is
recursive and stable, and duplicate ID/version pairs are rejected.

### 4. Variable schemas remain intentionally small

Variables support required, optional, and defaulted behavior plus six value
types: string, integer, number, boolean, list, and mapping. This supplies useful
runtime validation without introducing a second general-purpose schema system.

### 5. Artifact manifests are deterministic

Successful non-dry-run executions may write a versioned JSON manifest. Each
written artifact records its E-008 result state, source template, and SHA-256
digest. Manifests contain no timestamps or machine-specific paths.

### 6. Execution is a composition service

`TemplateExecutor` resolves and validates an E-009 definition, converts it to
an E-008 request, delegates to `GenerationEngine`, and writes a manifest only
after successful generation. It does not duplicate filesystem or safety logic.

### 7. Safe behavior remains explicit

Dry-runs never write artifacts or manifests. Overwrite remains disabled unless
the caller explicitly enables it. E-008 path-boundary and secret detection
policies apply unchanged.

### 8. CLI remains an adapter

The `generate templates` commands list, inspect, validate, and run definitions
through the same domain services used by programmatic consumers. Business
logic does not depend on Typer or Rich.

## Consequences

- Later plugin, provider, theme, workflow, and project generators can publish
  definitions without implementing new rendering or write pipelines.
- Generated output can be checked for missing or modified artifacts.
- Template variables fail before rendering when names or types are invalid.
- A future external/user template precedence model can add repository
  composition without changing the E-008 engine.
