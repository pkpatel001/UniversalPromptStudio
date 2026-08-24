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
values, or node configuration in schema 1. Runtime input values-including
prompt text-will arrive through declared workflow inputs in a later execution
checkpoint.

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

Execution planning, handler registration, and execution remain separate later
checkpoints.

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
legacy backend workflow placeholder. Typed planning and explicit host handler
registration remain E-016.4.
