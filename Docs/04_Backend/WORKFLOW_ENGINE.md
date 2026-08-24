# Workflow engine

E-016 provides the Engineering-owned workflow contract used by future
application workflow features. It is deliberately narrower than a visual or
long-running workflow engine.

## Supported boundary

- strict schema-1 directed acyclic graphs;
- explicit typed workflow and node ports;
- bounded passive discovery and compatible catalogs;
- controlled scaffold generation through E-009/E-008;
- trusted host-created operation registration;
- deterministic topological planning;
- controlled sequential execution of an already validated plan;
- deeply immutable, bounded JSON-shaped runtime values;
- fail-fast structured outcomes with validated completed-step results;
- existing 'WorkflowStarted' and 'WorkflowCompleted' application events; and
- host-authored offline echo and uppercase reference handlers.

The application container exposes the explicit operation registry, validated
offline reference plan, and controlled execution service. It does not replace
or reinterpret the early 'SequentialWorkflowEngine' placeholder.

## Execution policy

Each planned handler is rechecked against its registration snapshot immediately
before invocation and is called at most once. Inputs and outputs must exactly
match declared ports and types. The runner stops at the first drift, exception,
invalid output, aggregate transport overflow, or event-delivery failure. It
performs no automatic retry and never exposes raw exception text through the
portable failure contract.

Handlers are trusted in-process code, not sandboxed content. Workflow manifests
cannot load or construct handlers.

## Deferred product/runtime features

Parallel scheduling, conditions, branches with control-flow semantics, loops,
retries, cancellation, resume, persistence, long-running jobs, human approval,
remote triggers, streaming, dynamic plugin operations, and the visual editor
remain later application work after the Engineering Toolkit closes.
