# Workflow development

Author 'workflow-manifest.yaml' as strict data. Every mapping rejects unknown
keys and every collection is bounded.

## Minimal example

    schema_version: 1
    workflow:
      id: example.echo-workflow
      name: Echo workflow
      version: 1.0.0
      sdk_version: 1
      description: Pass text through a host-recognized echo operation.
      inputs:
        - id: prompt
          type: string
          description: Text supplied by the caller.
      outputs:
        - id: result
          type: string
          description: Text returned to the caller.
      nodes:
        - id: echo
          operation: ups.echo-text
          inputs:
            - id: text
              type: string
              description: Text to echo.
          outputs:
            - id: text
              type: string
              description: Echoed text.
      edges:
        - source:
            workflow_input: prompt
          target:
            node: echo
            port: text
        - source:
            node: echo
            port: text
          target:
            workflow_output: result

Operation IDs are host vocabulary, not Python or JavaScript import paths.
Manifest authors cannot supply implementations, commands, credentials, default
values, or node configuration in schema 1. Runtime values, including prompt
text, arrive only through declared workflow inputs in a typed
'WorkflowRunRequest'.

Validate the file directly with 'python -m Engineering workflow inspect
MANIFEST'. Repository-wide passive validation also recognizes the exact
filename through 'python -m Engineering manifest validate'.

For catalog admission, every input must be used and every node must contribute
to at least one workflow output. Duplicate ID/version pairs across explicit
roots are rejected. Use 'workflow validate --root ROOT' before publishing a
definition directory.

Discovery never scans implicit user or system locations. It prunes symlinks and
ignored dependency/build/cache directories, limits depth and manifest count,
and rejects manifests larger than one MiB. Multiple roots use caller-assigned
stable labels and retain their provenance.

Handler registration, planning, and execution are explicit host operations
with separate validation boundaries.

## Generate a starter

Use the controlled scaffold when beginning a schema-1 workflow:

    python -m Engineering generate workflow example.echo-flow \
      --name "Echo workflow" \
      --description "Pass text through a recognized operation." \
      --operation ups.echo-text \
      --dry-run

Remove '--dry-run' to write under 'Workflows/example-echo-flow'. Generation
creates the canonical manifest and an author README through the shared
E-009/E-008 pipeline. Existing files conflict by default; '--overwrite' is an
explicit replacement choice.

The generated manifest is intentionally minimal and already satisfies the graph
contract: workflow input 'input' binds to node 'step' input 'value', and that
node output binds to workflow output 'output'. Change the manifest as data after
generation, then run 'workflow inspect' and 'workflow validate'.

Generation does not create operation code, import a handler, plan a graph,
execute a node, contact a service, inspect credentials, or integrate with the
legacy backend workflow placeholder. E-016.4 planning is a separate
non-executing host operation.

## Register and plan in a trusted host

The application composition root creates handler objects and registers them
explicitly:

    registry = WorkflowOperationRegistry()
    registry.register(host_created_handler)
    report = WorkflowPlanner(registry).plan(workflow_record)

A handler must expose the exact operation ID, 'WorkflowSdkVersion', ordered
'WorkflowPort' input/output tuples, and the future execution method. Registration
takes an immutable contract snapshot. It does not import the implementation or
call that method.

Check 'report.passed' before reading 'report.plan'. A successful plan lists every
node exactly once in deterministic topological order. A failed report contains
stable failure codes for incompatible workflow SDKs, invalid graphs, missing
handlers, handler SDK mismatches, and input or output contract mismatches.

Manifest order does not decide execution order when multiple nodes are ready;
the planner uses lexical node ID as its stable tie break. A handler port
description or order difference is an exact-contract mismatch, even when IDs
and types appear similar.

There is intentionally no CLI option for registering module paths or planning
against data-selected implementations. Execution accepts only an already
validated plan and host-created typed request.

## Execute a validated plan

Create the request only after obtaining a successful plan:

    request = WorkflowRunRequest(
        "run-1",
        (WorkflowPortValue("input", "Hello"),),
    )
    outcome = WorkflowExecutionService(event_sink).execute(plan, request)

Check 'outcome.succeeded'. Success exposes exact workflow outputs and all
validated step results. Failure exposes a stable code, safe message, optional
failing node/operation, and only the steps that finished with valid outputs.

The runner is fail-fast and sequential. It does not retry, continue past a
failure, or return the failed handler's raw result. Treat every handler as
trusted host code with full in-process authority; exception containment is not
sandboxing.

The application container registers the two host-authored offline handlers and
provides 'offline_workflow_plan' plus 'workflow_execution_service'. Its event
bridge maps value-free SDK lifecycle metadata to the existing Backend
'WorkflowStarted' and 'WorkflowCompleted' events. Runtime values and failure
messages never enter event payloads.

E-016 is now complete. E-017 Engineering Self-Generation is the next Engineering
Toolkit milestone. Visual workflow authoring and advanced execution semantics
remain post-toolkit application work.
