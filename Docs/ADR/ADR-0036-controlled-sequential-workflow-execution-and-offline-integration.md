# ADR-0036: Controlled sequential workflow execution and offline integration

**Status:** Accepted
**Milestone:** E-016.5

## Context

E-016.4 produces immutable plans bound to explicit host-created handlers but
never invokes them. The final Workflow Generation checkpoint must prove those
plans end to end without adding dynamic loading, unbounded Python values,
implicit retries, or ambiguous partial-result behavior. Application workflow
events and an early placeholder engine already exist, but neither defines the
Engineering-owned runtime boundary.

## Decision

Add deeply immutable 'WorkflowPortValue' transport. Values are copied from
JSON-shaped host data into mapping proxies and tuples. Transport rejects null,
non-finite numbers, arbitrary objects, cycles, excessive depth, oversized
strings/collections/keys, too many ports, and envelopes above 4,096 total value
nodes.

Add immutable 'WorkflowRunRequest', 'WorkflowStepResult',
'WorkflowRunSuccess', and 'WorkflowRunFailure' records. Failures use stable
codes and safe messages. They may contain validated results from steps completed
before the failure, but never the failed raw result or exception detail.

'WorkflowExecutionService' accepts only an existing 'WorkflowExecutionPlan' and
typed request. It:

1. validates exact workflow input IDs and types before emitting an event;
2. emits a value-free started event;
3. processes plan steps in their established topological order;
4. rechecks live handler identity, SDK, and port contracts before every call;
5. resolves inputs only from validated request or completed-node values;
6. invokes each handler no more than once;
7. validates and freezes exact output mappings and cumulative output bounds;
8. stops at the first failure without retrying or invoking later nodes; and
9. emits a value-free completed event with success/failure and step count.

A started-event delivery failure prevents execution. A completed-event delivery
failure after otherwise successful execution returns an event-delivery failure
with all completed steps. When an operational failure already exists, failure
event delivery does not replace that primary failure.

Add host-authored 'ups.echo-text' and 'ups.uppercase-text' handlers plus the
two-step 'ups.offline-text-flow' reference record. The Backend composition root
creates their explicit registry, plans the record, exposes the controlled
executor and plan, and maps SDK lifecycle events to existing
'WorkflowStarted'/'WorkflowCompleted' events. Event payloads exclude runtime
values and error messages.

The early 'SequentialWorkflowEngine' placeholder is not modified or silently
reinterpreted.

## Trust boundary

Handler execution is trusted in-process execution, not sandboxing. Exception
containment protects the portable outcome from ordinary handler exceptions and
raw error-text disclosure, but cannot prevent a trusted handler from accessing
host resources or causing side effects.

Workflow data still cannot select modules, entry points, constructors,
credentials, endpoints, permissions, or implementations. No dynamic discovery,
external handler loading, plugin operation registration, network acquisition,
subprocess, filesystem access, or credential lookup is performed by the
reference execution path.

## Consequences

- E-016 now provides authoring, validation, discovery, catalog, scaffolding,
  explicit registration, deterministic planning, sequential execution, safe
  events, and one offline application-integrated reference flow.
- Input/output transport and partial-result behavior are deterministic and
  centrally enforced.
- Events prove lifecycle transitions without leaking runtime content.
- Every handler is called at most once and no automatic retry occurs.
- Parallelism, branches with control-flow semantics, loops, retries,
  cancellation, persistence, resume, long-running jobs, scheduling, streaming,
  remote triggers, dynamic external operations, and visual authoring remain
  deferred.
- E-017 Engineering Self-Generation is the next Engineering Toolkit milestone.
