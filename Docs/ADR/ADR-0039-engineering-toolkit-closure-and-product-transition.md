# ADR-0039: Engineering Toolkit closure and product transition

**Status:** Accepted
**Milestone:** E-017.3

## Context

E-001 through E-017 established the repository engineering foundations and the
plugin, provider, theme, workflow, and controlled self-generation boundaries.
Continuing toolkit-first work would delay validation of the actual desktop
product and encourage speculative abstractions.

## Decision

The Engineering Toolkit is closed as application-ready at E-017.3. Future work
will proceed through thin application vertical slices. Toolkit changes require
evidence of a concrete missing capability from an active slice.

The repository remains at `0.2.0-alpha`. Closure proves engineering readiness,
not beta product readiness. The immediate application checkpoint is A-001.1, a
narrow versioned and allowlisted desktop-to-Python IPC foundation.

The supported and deferred boundaries are recorded in
`ENGINEERING_TOOLKIT_CAPABILITY_MATRIX.md`. The closure evidence and version
recommendation are recorded in `ENGINEERING_TOOLKIT_READINESS.md`.

## Consequences

- Product outcomes, not new framework breadth, determine roadmap priority.
- Completed Engineering milestones are not reopened without a demonstrated
  regression or application requirement.
- The first application slice must preserve the existing composition-root and
  trust boundaries.
- Publishing, signing, dependency installation, automatic Git actions, and
  arbitrary code execution remain outside this decision.
