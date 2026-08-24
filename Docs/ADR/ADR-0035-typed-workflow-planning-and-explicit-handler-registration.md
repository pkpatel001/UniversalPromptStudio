# ADR-0035: Typed workflow planning and explicit handler registration

**Status:** Accepted
**Milestone:** E-016.4

## Context

E-016.1 through E-016.3 provide strict workflow graphs, compatible catalogs, and
controlled passive scaffolds. A future runner needs a deterministic plan and a
trusted binding from each declarative operation ID to a host implementation.
Allowing workflow data to select module paths or construct handlers would turn
the manifest into a code-loading instruction. Executing during registration or
planning would also collapse distinct validation and runtime trust boundaries.

## Decision

Define 'WorkflowOperationHandler' as the structural contract for one
already-created host handler. It exposes a vendor-qualified operation ID,
'WorkflowSdkVersion', exact ordered input and output 'WorkflowPort' tuples, and
an execution method reserved for the later runner.

'WorkflowOperationRegistry' is host-owned. Registration snapshots those
contract fields into an immutable 'WorkflowOperationRegistration', validates
their types and identities, and rejects duplicate operation IDs. Exact resolve
and unregister operations fail explicitly when a binding is absent. Registry
listing is lexical by operation ID. Registration never calls the execution
method.

'WorkflowPlanner' accepts a 'WorkflowRecord' and explicit registry. Planning
proceeds in this order:

1. require host SDK compatibility;
2. revalidate all producer-owned graph invariants;
3. resolve every node operation in lexical node-ID order;
4. require exact handler SDK, input tuple, and output tuple equality; and
5. use Kahn topological ordering with lexical node-ID tie breaking.

Exact port equality includes identifier, value type, description, and declared
order. A successful immutable plan contains every node once, contiguous
zero-based positions, sorted dependencies, exact incoming edges, snapshotted
handler registrations, and workflow-output bindings.

Failures are returned as immutable 'WorkflowPlanningFailure' values with stable
codes, paths, safe messages, and optional node/operation identity. Planning
returns either one plan or one or more failures, never both.

No CLI is added. There is no approved data-driven mechanism for constructing or
loading handlers, so a CLI planning command would either be nonfunctional or
weaken the explicit host-registration boundary.

## Trust boundary

A workflow operation ID remains descriptive host vocabulary. It is not an
import path, entry point, constructor, permission grant, endpoint, or proof of
trust. Only trusted host code creates and registers handler objects.

Registration may inspect handler contract properties but does not call the
execution method. Planning does not import modules, discover implementations,
instantiate handlers, invoke operations, access credentials, contact services,
launch subprocesses, read or write workflow files, emit events, or mutate
application state.

The execution method exists in the protocol so E-016.5 can build a controlled
runner around the same explicit binding. Its generic mapping signature does not
approve arbitrary transport: E-016.5 must add bounded typed value validation,
structured run outcomes, and exception containment before invocation.

## Consequences

- Compatible workflow graphs have reproducible execution order independent of
  manifest node/edge order and registry insertion order.
- Every planned node is bound to one exact immutable handler-contract snapshot.
- Missing handlers and SDK or port drift fail closed with structured evidence.
- Workflow data cannot load or construct executable code.
- Handler invocation, runtime input/output validation, events, partial-result
  policy, retries, persistence, scheduling, and backend integration remain
  E-016.5 concerns.
