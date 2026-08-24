# ADR-0034: Controlled passive workflow scaffold generation

**Status:** Accepted
**Milestone:** E-016.3

## Context

E-016.1 and E-016.2 define, validate, discover, and catalog passive workflow
graphs. Authors need a canonical starter, but a WorkflowSystem-specific
renderer or writer would duplicate the established E-009 template and E-008
generation safety boundaries. Generating operation code would also confuse a
declarative operation identifier with a trusted implementation.

## Decision

Add the versioned built-in 'workflow.declarative-basic' definition with exactly
two authored artifacts: 'workflow-manifest.yaml' and 'README.md'. The manifest
contains one string workflow input, one operation node with string ports, one
string workflow output, and two explicit directed edges. The operation ID is
caller-selectable but must satisfy the existing vendor-qualified identity
contract.

WorkflowScaffoldService owns domain input construction and verification. It
builds the immutable WorkflowManifest, serializes its exact data, and validates
that serialization through WorkflowManifestReader before delegating. This
pre-write pass also enforces the existing secret-content and graph rules.

E-009 owns definition resolution, variable validation, orchestration, and the
deterministic '.ups-artifact-manifest.json'. E-008 owns rendering, destination
containment, dry-run, default conflict rejection, explicit overwrite, writes,
and rollback. WorkflowSystem rereads every successful non-dry-run manifest and
requires exact semantic equality with the validated request.

The default destination is 'Workflows/<workflow-id-with-dots-as-hyphens>'.
Supplied destinations must be exactly one direct child of 'Workflows/'. The CLI
is a thin adapter over the service.

## Trust boundary

The template emits no operation implementation or executable source. An
operation ID remains host vocabulary, not an import path, registration request,
or proof of a trusted handler. Scaffold generation does not import modules,
register handlers, plan execution, execute nodes, access credentials, contact
services, launch subprocesses, or integrate the legacy backend workflow engine.

## Consequences

- Authors receive one deterministic, immediately valid schema-1 starter.
- Dry-run, conflicts, overwrites, path safety, artifact hashes, and rollback
  retain the established shared generation semantics.
- Invalid and secret-like manifest content fails before any scaffold write.
- Post-generation producer reread detects template/domain drift.
- E-016.4 remains responsible for typed planning and explicit host-created
  handler registration.

