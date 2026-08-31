# ADR-0043: Bounded local prompt management without a schema migration

**Status:** Accepted
**Date:** 2026-08-31
**Checkpoint:** A-002.2

## Context

A-002.1 established schema-1 SQLite storage for projects, project-owned prompts,
categories, tags, ordered blocks, creation/update timestamps, and foreign-key
relationships. The desktop exposed only creation and listing. A-002.2 needed a
usable management lifecycle without weakening the closed desktop boundary or
rewriting existing user databases unnecessarily.

## Decision

- Retain SQLite schema version 1. All A-002.2 persisted values already have
  owned schema-1 columns and tables.
- Add application-service use cases for owned prompt detail/update/delete,
  deterministic project-scoped search, and project deletion.
- Treat the submitted block array as the authoritative order and persist
  normalized zero-based order values.
- Bound prompts to 12 blocks, 2,000 characters per block, and 12,000 block
  characters in total. Bound categories to 80 characters and tags to 10 unique
  case-insensitive single-line values of at most 32 characters.
- Search synchronously and deterministically within one project across title,
  category, tags, and block content. Do not introduce background indexing.
- Require exact `confirm: true` payloads for deletion. Prompt deletion enforces
  ownership. SQLite project deletion removes dependent prompts in the same
  repository transaction and reports the count.
- Expand the closed Python/Rust/webview command surface from five to ten fixed
  commands. Every layer independently validates exact shapes and bounds.

## Consequences

- Existing schema-1 databases open unchanged and edits survive restart.
- Organization remains embedded in prompt records; there are no category/tag
  catalog tables or migrations.
- Local search is predictable and adequate for the bounded library, but has no
  fuzzy ranking, cross-project scope, or background index.
- Deletion is irreversible through the current application UI.
- Prompt composition and execution remain outside this decision and begin in
  A-003.
