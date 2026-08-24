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

Discovery, catalogs, generation, planning, handler registration, and execution
remain separate later checkpoints.
