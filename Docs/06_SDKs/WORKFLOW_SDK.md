# Workflow SDK

E-016.1 defines a passive, portable workflow authoring contract. A workflow
manifest describes identity, typed ports, host-recognized operation IDs, and
directed data-flow bindings. Reading a manifest does not import or execute an
operation.

## Contract

The canonical filename is 'workflow-manifest.yaml'. Schema 1 requires:

- a vendor-qualified workflow ID and canonical major.minor.patch version;
- Workflow SDK API level 1;
- bounded name and description text;
- explicit workflow input and output ports;
- one or more uniquely identified nodes;
- a vendor-qualified operation ID and exact ports for every node; and
- explicit edges from workflow inputs or node outputs to node inputs or workflow outputs.

Port types are closed to string, integer, number, boolean, object, and array.
Null, unions, defaults, configuration values, executable expressions, entry
points, paths, URLs, environment lookups, and credentials are not part of
schema 1.

Every node input and workflow output has exactly one incoming binding. Sources
must exist, targets must exist, connected types must match, and the whole graph
must be acyclic. Disconnected cycles are invalid.

## Compatibility

'schema_version' governs the YAML document shape. 'workflow.sdk_version'
governs both the authoring contract and operation-handler contract. E-016.4
planning and E-016.5 execution enforce exact equality; the manifest cannot
select, load, configure, or invoke a handler.

The shared manifest system registers this family as 'ups.workflow' and permits
multiple workflow manifests below an inspected root.

## Passive inspection

Run 'python -m Engineering workflow inspect MANIFEST'. The command validates
and summarizes one document. It performs no handler imports, operation
execution, network request, credential lookup, subprocess, or filesystem write.

## Discovery and compatibility

E-016.2 discovers only the exact canonical filename below one or more explicit,
labeled roots. Roots, directory traversal, and manifest files are symlink-safe.
Dependency, cache, VCS, build, distribution, and Rust target directories are
ignored. Discovery is bounded to:

- 16 directory levels;
- 1,024 workflow manifests per root; and
- 1,048,576 bytes per manifest.

Records retain root ID and portable relative-path provenance. Duplicate workflow
ID/version pairs fail; root order never creates implicit precedence.

The current host supports Workflow SDK API level 1 only. Structurally valid
future or legacy SDK definitions remain inspectable but are excluded from the
compatible catalog with a stable 'workflow.sdk.incompatible' issue.

Compatible records are ordered by workflow ID and semantic version. Programmatic
catalog resolution returns an exact requested version or the highest compatible
version and can require a set of declared operation IDs. Catalog operations
remain metadata-only.

E-016.2 also requires every declared workflow input to feed an edge and every
node to contribute to a workflow output. These checks complement exact
references, single target bindings, type matching, and global acyclicity.

Use:

- 'python -m Engineering workflow list --root ROOT'
- 'python -m Engineering workflow validate --root ROOT'

Repeat '--root' for multiple roots. These commands preserve provenance and
perform no import, registration, planning, execution, network access, credential
lookup, subprocess, or write.

## Controlled scaffold generation

E-016.3 adds one built-in 'workflow.declarative-basic' template. Generate its
canonical passive starter with:

    python -m Engineering generate workflow example.echo-flow \
      --operation example.echo-text

Use '--dry-run' to preview both artifacts without writing and '--overwrite'
only when replacement is intentional. The default destination is one direct
child of 'Workflows/' derived from the workflow ID; a custom destination must
preserve that boundary.

The scaffold contains exactly 'workflow-manifest.yaml' and 'README.md', plus the
E-009 '.ups-artifact-manifest.json' integrity record. The starter has one string
input, one host-recognized operation node, one string output, and two explicit
edges. It generates no operation implementation or other executable code.

WorkflowSystem validates the complete requested manifest before delegation,
E-009 resolves the versioned template and records artifact hashes, and E-008
owns rendering, destination safety, dry-run, conflict handling, writes, and
rollback. After a successful write, WorkflowSystem rereads the generated
manifest and requires exact semantic equality with the validated request.

## Typed non-executing planning

E-016.4 adds 'WorkflowOperationHandler' as a structural contract for an
already-created host handler. A handler declares one vendor-qualified operation
ID, its Workflow SDK API level, exact ordered input and output port tuples, and
an execution method for the later runner. Registration snapshots this metadata
and does not call the method.

'WorkflowOperationRegistry' rejects malformed contracts, duplicate operation
IDs, and missing exact lookups. It never imports, discovers, instantiates, or
replaces a handler. The trusted composition root is responsible for constructing
and registering handler objects.

'WorkflowPlanner' accepts one compatible 'WorkflowRecord' and one explicit
registry. It revalidates graph invariants, requires a registered handler for
every node, and matches the workflow SDK level plus the complete ordered input
and output port contracts. Port equality includes ID, type, description, and
order.

Planning returns either an immutable 'WorkflowExecutionPlan' or a deterministic
tuple of 'WorkflowPlanningFailure' values. Successful steps are ordered with
Kahn topological sorting and a lexical node-ID tie break. Each step carries its
snapshotted handler registration, sorted node dependencies, and exact incoming
bindings; workflow-output bindings are retained on the plan.

Planning does not call 'execute', resolve module paths, import operations,
contact a service, access credentials, launch a subprocess, write files, or
change application state. There is no planning CLI because workflow data cannot
select or load a handler. The controlled runner below accepts only an explicit
plan and bounded typed request before calling a registered method.

## Controlled sequential execution

E-016.5 executes only an existing 'WorkflowExecutionPlan'. A
'WorkflowRunRequest' supplies a bounded run ID and exact named workflow inputs.
Every 'WorkflowPortValue' is copied into deeply immutable containers before a
handler can observe it.

Runtime transport accepts strings, finite integers/numbers, booleans, objects,
and arrays. Null and arbitrary Python objects are rejected. Bounds are:

- 65,536 characters per string;
- 256 entries or items per object or array;
- 128 characters per object key;
- eight nested collection levels;
- 128 named ports per request or result envelope; and
- 4,096 scalar/collection nodes for inputs and cumulatively completed outputs.

The sequential runner rechecks each live handler against its immutable
registration snapshot, resolves inputs only from validated workflow inputs or
completed node outputs, and invokes the handler once. Returned mappings must
have exactly the declared keys and value types and pass the same deep bounds.

A successful 'WorkflowRunSuccess' contains exact workflow outputs and validated
step results. 'WorkflowRunFailure' uses stable codes for invalid input, handler
drift, contained handler exceptions, invalid output, and lifecycle-event
delivery failure. Execution stops at the first failure, performs no retry, and
retains only validated results from steps completed before that failure. Raw
exception type, text, inputs, and outputs are excluded from failure messages and
events.

'WorkflowStarted' is emitted only after request inputs validate. A value-free
'WorkflowCompleted' event records success/failure code and completed-step count.
If start-event delivery fails, no handler runs. If success-event delivery fails
after all handlers run, the outcome is an event-delivery failure that records
the completed steps.

The built-in 'ups.offline-text-flow' binds trusted host-created
'ups.echo-text' and 'ups.uppercase-text' handlers. It runs deterministically
without imports, filesystem access, subprocesses, credentials, or network
requests. The application composition root exposes its registry, plan, executor,
and safe event bridge while preserving the legacy placeholder engine.

E-016 is complete at this boundary. Handlers remain trusted in-process code, not
a sandbox. Parallelism, retries, cancellation, persistence, resume, scheduling,
dynamic external handlers, streaming, and visual authoring remain deferred.
