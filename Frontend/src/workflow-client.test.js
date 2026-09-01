import assert from "node:assert/strict";
import test from "node:test";

import {
  definitionViewToInput,
  PROMPT_WORKFLOW_OPERATION,
  validateExecution,
  validateOperationCatalog,
  validatePlan,
  WorkflowClient,
} from "./workflow-client.js";

const operationPort = (portId, description) => ({ portId, valueType: "string", description });
const definitionPort = (id, description) => ({ id, type: "string", description });

const operations = {
  operations: [
    {
      operationId: "ups.echo-text", sdkVersion: 1, requiresProvider: false,
      inputs: [operationPort("value", "Text supplied to the operation.")],
      outputs: [operationPort("value", "Text returned by the operation.")],
    },
    {
      operationId: PROMPT_WORKFLOW_OPERATION, sdkVersion: 1, requiresProvider: true,
      inputs: [
        operationPort("project-id", "Owning durable project identifier."),
        operationPort("prompt-id", "Durable project-owned prompt identifier."),
        operationPort("provider-id", "Existing host-authorized provider identifier selected for this run."),
      ],
      outputs: [operationPort("result", "Bounded text returned by the authorized provider.")],
    },
    {
      operationId: "ups.uppercase-text", sdkVersion: 1, requiresProvider: false,
      inputs: [operationPort("value", "Text supplied to the operation.")],
      outputs: [operationPort("value", "Text returned by the operation.")],
    },
  ],
};

const definition = {
  schemaVersion: 1,
  workflow: {
    id: "ups.user-echo", name: "User Echo", version: "1.0.0", sdkVersion: 1,
    description: "Bounded user-authored echo workflow.",
    inputs: [definitionPort("input", "Workflow text.")],
    outputs: [definitionPort("output", "Workflow result.")],
    nodes: [{
      id: "echo", operation: "ups.echo-text",
      inputs: [definitionPort("value", "Text supplied to the operation.")],
      outputs: [definitionPort("value", "Text returned by the operation.")],
    }],
    edges: [
      { source: { workflowInput: "input" }, target: { node: "echo", port: "value" } },
      { source: { node: "echo", port: "value" }, target: { workflowOutput: "output" } },
    ],
  },
};

const definitionView = {
  schemaVersion: 1,
  workflow: {
    ...definition.workflow,
    edges: [
      {
        source: { kind: "workflow-input", portId: "input", nodeId: null },
        target: { kind: "node", portId: "value", nodeId: "echo" },
      },
      {
        source: { kind: "node", portId: "value", nodeId: "echo" },
        target: { kind: "workflow-output", portId: "output", nodeId: null },
      },
    ],
  },
};

const plan = {
  plan: {
    valid: true, summary: "Workflow planning succeeded: 1 steps, 0 failures.",
    workflowId: "ups.user-echo", version: "1.0.0", failures: [],
    steps: [{ position: 0, nodeId: "echo", operationId: "ups.echo-text", dependencies: [] }],
  },
};

test("workflow client invokes only the eight fixed A-005 commands", async () => {
  const calls = [];
  const invokeCommand = async (command, payload) => {
    calls.push({ command, payload });
    if (command === "workflow_operations") return operations;
    if (command === "workflows") return { workflows: [{ workflowId: "ups.user-echo", name: "User Echo", version: "1.0.0", description: "Bounded user-authored echo workflow.", nodeCount: 1, edgeCount: 2 }], hasMore: false };
    if (["workflow_create", "workflow_get", "workflow_update"].includes(command)) return { workflow: definitionView };
    if (command === "workflow_delete") return { deletedWorkflowId: "ups.user-echo" };
    if (command === "workflow_plan") return plan;
    if (command === "workflow_execute") return {
      execution: {
        runId: payload.runId, workflowId: "ups.user-echo", version: "1.0.0",
        succeeded: true, completedStepCount: 1, failure: null,
        outputs: [{ portId: "output", value: "bounded" }],
        steps: [{ position: 0, nodeId: "echo", operationId: "ups.echo-text", outputs: [{ portId: "value", value: "bounded" }] }],
      },
    };
    throw new Error("unexpected command");
  };
  const client = new WorkflowClient(invokeCommand, () => "workflow-request");

  await client.listOperations();
  await client.listWorkflows();
  await client.createWorkflow(definition);
  await client.getWorkflow("ups.user-echo");
  await client.updateWorkflow("ups.user-echo", definition);
  await client.deleteWorkflow("ups.user-echo", true);
  await client.planWorkflow("ups.user-echo");
  const result = await client.executeWorkflow("ups.user-echo", [{ portId: "input", value: "bounded" }], true);

  assert.deepEqual(calls.map((call) => call.command), [
    "workflow_operations", "workflows", "workflow_create", "workflow_get",
    "workflow_update", "workflow_delete", "workflow_plan", "workflow_execute",
  ]);
  assert.equal(calls.at(-1).payload.confirm, true);
  assert.equal(result.execution.outputs[0].value, "bounded");
  assert.deepEqual(definitionViewToInput(definitionView), definition);
});

test("frontend rejects arbitrary operations, null runtime values, and malformed outcomes", async () => {
  const arbitrary = structuredClone(definition);
  arbitrary.workflow.nodes[0].operation = "evil.dynamic";
  const client = new WorkflowClient(async () => assert.fail("backend should not be invoked"), () => "workflow-request");

  assert.throws(() => client.createWorkflow(arbitrary), /not authorized|node is invalid/i);
  assert.throws(() => client.executeWorkflow("ups.user-echo", [{ portId: "input", value: null }], true), /null|invalid/i);
  assert.throws(() => validatePlan({ plan: { ...plan.plan, valid: false } }, "ups.user-echo"));
  assert.throws(() => validateExecution({ execution: { runId: "x" } }, "ups.user-echo", "x"));
});

test("operation catalog requires exact trusted contracts and provider marker", () => {
  assert.equal(validateOperationCatalog(operations).operations[1].requiresProvider, true);
  const changed = structuredClone(operations);
  changed.operations[1].requiresProvider = false;
  assert.throws(() => validateOperationCatalog(changed));
});
