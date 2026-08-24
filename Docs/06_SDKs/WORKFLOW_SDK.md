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
governs both the authoring contract and the operation-handler contract that a
future execution planner will enforce. E-016.1 defines no handler registry or
runtime.

The shared manifest system registers this family as 'ups.workflow' and permits
multiple workflow manifests below an inspected root.

## Passive inspection

Run 'python -m Engineering workflow inspect MANIFEST'. The command validates
and summarizes one document. It performs no handler imports, operation
execution, network request, credential lookup, subprocess, or filesystem write.
