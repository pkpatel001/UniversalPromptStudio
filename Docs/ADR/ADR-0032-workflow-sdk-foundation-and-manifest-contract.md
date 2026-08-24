# ADR-0032: Workflow SDK foundation and manifest contract

**Status:** Accepted
**Milestone:** E-016.1

## Context

The repository has an application-facing sequential workflow placeholder but no
portable Engineering-owned workflow definition. The foundation must establish
graph and data-flow meaning without turning YAML into a programming language or
silently replacing the backend abstraction.

## Decision

'Engineering.WorkflowSystem' owns schema 1 of the exact filename
'workflow-manifest.yaml'. All fields are required, mappings reject unknown
keys, collections and text are bounded, and models are immutable.

Ports use the smallest useful JSON-shaped vocabulary: string, integer, number,
boolean, object, and array. Null, union types, and default values are excluded.
Prompt and other runtime values enter only through declared workflow inputs;
schema 1 contains no node configuration field.

Workflow inputs and outputs are boundary ports. Edges bind them explicitly to
node ports rather than representing them as magic nodes. Each node references a
vendor-qualified host operation ID. Operation IDs are never module paths or
implicit loading instructions.

Every node input and workflow output has exactly one incoming binding.
References must exist and connected port types must match. Schema 1 forbids
every directed cycle, including cycles disconnected from workflow outputs.
These document invariants are enforced during producer-owned reading; E-016.2
will add bounded discovery, compatibility, catalog behavior, and graph
hardening across discovered records.

The Workflow SDK level governs the authoring contract and the future
host-handler planning contract. It grants no execution permission.

'ups.workflow' is a plural shared manifest family whose adapter delegates to
the workflow-owned reader. 'workflow inspect' is the only domain CLI surface in
this checkpoint.

## Trust boundary

Inspection uses safe YAML and performs no operation import, handler
registration, execution, network request, credential access, subprocess, or
write. Secret-like keys and high-confidence secret-bearing values are rejected.
There is no embedded code, expression, shell command, environment lookup,
credential reference, executable entry point, path, or URL field.

## Consequences

- Workflow authors gain a deterministic typed DAG and stable issue codes.
- Future planning can match exact operation and port contracts without data-driven imports.
- The legacy backend 'WorkflowEngine' remains unchanged.
- Discovery, catalogs, scaffold generation, execution planning, handler
  registration, execution, persistence, retries, branches, scheduling, and UI
  work remain deferred.
