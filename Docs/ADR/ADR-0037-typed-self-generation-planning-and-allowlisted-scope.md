# ADR-0037: Typed self-generation planning and allowlisted scope

**Status:** Accepted
**Milestone:** E-017.1

## Context

The Engineering Toolkit now has documentation, code generation, templates,
build and release contracts, shared manifests, and domain-owned plugin,
provider, theme, and workflow generation. Its final milestone must prove those
capabilities can create future Engineering structures reproducibly without
turning repository content into instructions for autonomous self-modification.

A request containing a repository path or template identifier would bypass
domain ownership and make the trust boundary too broad. Executing generation in
the first checkpoint would also mix the definition of approved scope with
filesystem mutation.

## Decision

Define self-generation as a human-requested, human-reviewed, allowlisted plan
that will use the existing E-009/E-008 pipeline in E-017.2. E-017.1 is strictly
read-only.

Add immutable request, artifact, prerequisite, issue, plan, and dry-run report
models under `Engineering.SelfGeneration`. The only request target is a new
Engineering subsystem. Callers provide validated package/module identifiers,
bounded display text, and an optional CLI-placeholder choice. They cannot
provide a destination, artifact path, template ID, import path, command, or
overwrite policy.

The closed artifact inventory derives these destinations:

1. `Engineering/{Package}/__init__.py`;
2. `Engineering/{Package}/{module}.py`;
3. `Engineering/Tests/test_{module}.py`;
4. `Engineering/{Package}/README.md`; and
5. optionally, `Engineering/cli/commands/{module}.py`.

Each artifact has a fixed host-owned renderer key. These keys are planning
vocabulary only in E-017.1; there is no template resolution or execution.

Before a plan is ready, a read-only checker requires exact regular,
non-symlinked repository evidence for every milestone from E-007 through E-016.
Planning also requires the UPS project marker, rejects symlinked destination
components, and reports every existing destination as a default no-overwrite
conflict. Results and issues retain stable milestone, artifact, and lexical
ordering.

`dry_run` returns a deterministic text projection ending with an explicit
no-write statement. It calls the same planner and does not simulate writes by
creating directories or temporary files.

## Security boundary

The project root is supplied by trusted host composition, not request data.
Request validation rejects separators, traversal forms, control characters,
unbounded text, and malformed identifiers. The planner does not import
milestone modules, load plugins or handlers, resolve templates, render code,
read credentials or environment variables, contact a service, launch a
subprocess, execute commands, or write files.

This is scope control, not a sandbox. Trusted Python code could replace module
constants or call lower-level generation APIs directly. Hosts must expose only
the typed planner to untrusted request sources and must continue to review every
future generated diff.

## Consequences

- E-017 has an explicit, testable meaning that excludes autonomous
  self-modification.
- Safe and useful initial artifact families and destinations are inventoried in
  code and documentation.
- Readiness depends on the completed E-007 through E-016 stack rather than
  silently bypassing it.
- Plans and dry-run reports are reproducible for identical repository state.
- E-017.2 is the next checkpoint: add approved templates, controlled
  transactional execution, artifact-manifest evidence, and drift verification.
- Automatic commits, pushes, releases, publishing, dependency installation,
  arbitrary commands, arbitrary paths/templates, and security-sensitive core
  replacement remain forbidden.
