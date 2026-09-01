import { invoke } from "@tauri-apps/api/core";

import { BackendClientError } from "./backend-client.js";

const REQUEST_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const LOCAL_ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const VENDOR_ID = /^[a-z0-9]+(?:-[a-z0-9]+)*(?:\.[a-z0-9]+(?:-[a-z0-9]+)*)+$/;
const VERSION = /^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$/;
const VALUE_TYPES = new Set(["string", "integer", "number", "boolean", "object", "array"]);
const PLAN_FAILURES = new Set([
  "workflow-incompatible", "graph-invalid", "handler-missing", "handler-sdk-mismatch",
  "handler-input-mismatch", "handler-output-mismatch",
]);
const RUN_FAILURES = new Set([
  "input-invalid", "handler-drift", "handler-error", "output-invalid", "event-delivery-failed",
]);
const SAFE_ERRORS = new Set([
  "backend.unavailable", "library.invalid_input", "library.not_found", "storage.unavailable",
  "workflow.storage_invalid",
]);

export const PROMPT_WORKFLOW_OPERATION = "ups.execute-saved-prompt";

const operationContract = Object.freeze({
  "ups.echo-text": Object.freeze({
    inputs: [port("value", "Text supplied to the operation.")],
    outputs: [port("value", "Text returned by the operation.")],
  }),
  [PROMPT_WORKFLOW_OPERATION]: Object.freeze({
    inputs: [
      port("project-id", "Owning durable project identifier."),
      port("prompt-id", "Durable project-owned prompt identifier."),
      port("provider-id", "Existing host-authorized provider identifier selected for this run."),
    ],
    outputs: [port("result", "Bounded text returned by the authorized provider.")],
  }),
  "ups.uppercase-text": Object.freeze({
    inputs: [port("value", "Text supplied to the operation.")],
    outputs: [port("value", "Text returned by the operation.")],
  }),
});

function port(id, description) {
  return Object.freeze({ portId: id, valueType: "string", description });
}

export class WorkflowClient {
  constructor(invokeCommand = invoke, requestIdFactory = () => crypto.randomUUID()) {
    if (typeof invokeCommand !== "function" || typeof requestIdFactory !== "function") {
      throw invalid("Workflow client is invalid.");
    }
    this.invokeCommand = invokeCommand;
    this.requestIdFactory = requestIdFactory;
  }

  listOperations() {
    return this.#invoke("workflow_operations", {}, validateOperationCatalog);
  }

  listWorkflows() {
    return this.#invoke("workflows", {}, validateWorkflowList);
  }

  createWorkflow(workflow) {
    const normalized = validateDefinitionInput(workflow);
    return this.#invoke("workflow_create", { workflow: normalized }, (value) =>
      validateDefinitionResult(value, normalized.workflow.id));
  }

  getWorkflow(workflowId) {
    const id = validateVendorId(workflowId);
    return this.#invoke("workflow_get", { workflowId: id }, (value) =>
      validateDefinitionResult(value, id));
  }

  updateWorkflow(workflowId, workflow) {
    const id = validateVendorId(workflowId);
    const normalized = validateDefinitionInput(workflow);
    if (normalized.workflow.id !== id) throw invalid("Workflow identity cannot change during update.");
    return this.#invoke("workflow_update", { workflowId: id, workflow: normalized }, (value) =>
      validateDefinitionResult(value, id));
  }

  deleteWorkflow(workflowId, confirmed) {
    const id = validateVendorId(workflowId);
    requireConfirmation(confirmed);
    return this.#invoke("workflow_delete", { workflowId: id, confirm: true }, (value) => {
      exact(value, ["deletedWorkflowId"]);
      if (value.deletedWorkflowId !== id) throw unavailable();
      return Object.freeze({ deletedWorkflowId: id });
    });
  }

  planWorkflow(workflowId) {
    const id = validateVendorId(workflowId);
    return this.#invoke("workflow_plan", { workflowId: id }, (value) => validatePlan(value, id));
  }

  executeWorkflow(workflowId, inputs, confirmed) {
    const id = validateVendorId(workflowId);
    requireConfirmation(confirmed);
    if (!Array.isArray(inputs) || inputs.length > 8) throw invalid("Workflow inputs are invalid.");
    const seen = new Set();
    const normalized = inputs.map((item) => {
      exact(item, ["portId", "value"]);
      const portId = validateLocalId(item.portId);
      if (seen.has(portId)) throw invalid("Workflow input ports must be unique.");
      seen.add(portId);
      validateRuntimeValue(item.value);
      return Object.freeze({ portId, value: structuredClone(item.value) });
    });
    const runId = crypto.randomUUID();
    return this.#invoke(
      "workflow_execute",
      { workflowId: id, runId, inputs: normalized, confirm: true },
      (value) => validateExecution(value, id, runId),
    );
  }

  async #invoke(command, payload, validator) {
    const requestId = this.requestIdFactory();
    if (typeof requestId !== "string" || !REQUEST_ID.test(requestId)) {
      throw invalid("Workflow request identifier is invalid.");
    }
    try {
      return validator(await this.invokeCommand(command, { requestId, ...payload }));
    } catch (error) {
      if (error instanceof BackendClientError) throw error;
      const code = error && typeof error === "object" ? error.code : null;
      const message = error && typeof error === "object" ? error.message : null;
      if (typeof code === "string" && SAFE_ERRORS.has(code) && typeof message === "string") {
        throw new BackendClientError(code, message);
      }
      throw unavailable();
    }
  }
}

export function definitionViewToInput(view) {
  const normalized = validateDefinitionView(view);
  return {
    schemaVersion: 1,
    workflow: {
      id: normalized.workflow.id,
      name: normalized.workflow.name,
      version: normalized.workflow.version,
      sdkVersion: 1,
      description: normalized.workflow.description,
      inputs: normalized.workflow.inputs.map(viewPortToInput),
      outputs: normalized.workflow.outputs.map(viewPortToInput),
      nodes: normalized.workflow.nodes.map((node) => ({
        id: node.id,
        operation: node.operation,
        inputs: node.inputs.map(viewPortToInput),
        outputs: node.outputs.map(viewPortToInput),
      })),
      edges: normalized.workflow.edges.map((edge) => ({
        source: viewEndpointToInput(edge.source),
        target: viewEndpointToInput(edge.target),
      })),
    },
  };
}

function viewPortToInput(value) {
  return { id: value.id, type: value.type, description: value.description };
}

function viewEndpointToInput(endpoint) {
  if (endpoint.kind === "workflow-input") return { workflowInput: endpoint.portId };
  if (endpoint.kind === "workflow-output") return { workflowOutput: endpoint.portId };
  return { node: endpoint.nodeId, port: endpoint.portId };
}

export function validateOperationCatalog(value) {
  exact(value, ["operations"]);
  const ids = Object.keys(operationContract);
  if (!Array.isArray(value.operations) || value.operations.length !== ids.length) throw unavailable();
  const operations = value.operations.map((operation, index) => {
    exact(operation, ["inputs", "operationId", "outputs", "requiresProvider", "sdkVersion"]);
    const expectedId = ids[index];
    if (
      operation.operationId !== expectedId || operation.sdkVersion !== 1 ||
      operation.requiresProvider !== (expectedId === PROMPT_WORKFLOW_OPERATION)
    ) throw unavailable();
    const inputs = validateOperationPorts(operation.inputs);
    const outputs = validateOperationPorts(operation.outputs);
    const expected = operationContract[expectedId];
    if (JSON.stringify(inputs) !== JSON.stringify(expected.inputs) || JSON.stringify(outputs) !== JSON.stringify(expected.outputs)) {
      throw unavailable();
    }
    return Object.freeze({ operationId: expectedId, sdkVersion: 1, inputs, outputs, requiresProvider: operation.requiresProvider });
  });
  return Object.freeze({ operations: Object.freeze(operations) });
}

function validateOperationPorts(values) {
  if (!Array.isArray(values) || values.length > 8) throw unavailable();
  return Object.freeze(values.map((value) => {
    exact(value, ["description", "portId", "valueType"]);
    return Object.freeze({
      portId: validateLocalId(value.portId),
      valueType: validateValueType(value.valueType),
      description: validateText(value.description, 500),
    });
  }));
}

export function validateWorkflowList(value) {
  exact(value, ["hasMore", "workflows"]);
  if (!Array.isArray(value.workflows) || value.workflows.length > 50 || value.hasMore !== false) throw unavailable();
  let previous = "";
  const workflows = value.workflows.map((item) => {
    exact(item, ["description", "edgeCount", "name", "nodeCount", "version", "workflowId"]);
    const workflowId = validateVendorId(item.workflowId);
    if (workflowId <= previous || !Number.isSafeInteger(item.nodeCount) || item.nodeCount < 1 || item.nodeCount > 8 || !Number.isSafeInteger(item.edgeCount) || item.edgeCount < 0 || item.edgeCount > 64) throw unavailable();
    previous = workflowId;
    return Object.freeze({
      workflowId,
      name: validateText(item.name, 120),
      version: validateVersion(item.version),
      description: validateText(item.description, 1_000),
      nodeCount: item.nodeCount,
      edgeCount: item.edgeCount,
    });
  });
  return Object.freeze({ workflows: Object.freeze(workflows), hasMore: false });
}

function validateDefinitionResult(value, expectedId) {
  exact(value, ["workflow"]);
  const workflow = validateDefinitionView(value.workflow);
  if (workflow.workflow.id !== expectedId) throw unavailable();
  return Object.freeze({ workflow });
}

export function validateDefinitionInput(value) {
  exact(value, ["schemaVersion", "workflow"]);
  if (value.schemaVersion !== 1) throw invalid("Workflow schema is invalid.");
  const workflow = validateWorkflowBodyInput(value.workflow);
  return Object.freeze({ schemaVersion: 1, workflow });
}

function validateWorkflowBodyInput(value) {
  exact(value, ["description", "edges", "id", "inputs", "name", "nodes", "outputs", "sdkVersion", "version"]);
  if (value.sdkVersion !== 1 || !Array.isArray(value.nodes) || value.nodes.length < 1 || value.nodes.length > 8 || !Array.isArray(value.edges) || value.edges.length > 64) throw invalid("Workflow definition is invalid.");
  const inputs = validateDefinitionPorts(value.inputs);
  const outputs = validateDefinitionPorts(value.outputs);
  const nodeIds = new Set();
  const nodes = value.nodes.map((node) => {
    exact(node, ["id", "inputs", "operation", "outputs"]);
    const id = validateLocalId(node.id);
    if (nodeIds.has(id) || !operationContract[node.operation]) throw invalid("Workflow node is invalid.");
    nodeIds.add(id);
    const nodeInputs = validateDefinitionPorts(node.inputs);
    const nodeOutputs = validateDefinitionPorts(node.outputs);
    const expected = operationContract[node.operation];
    if (!definitionPortsMatch(nodeInputs, expected.inputs) || !definitionPortsMatch(nodeOutputs, expected.outputs)) throw invalid("Workflow node ports are invalid.");
    return Object.freeze({ id, operation: node.operation, inputs: nodeInputs, outputs: nodeOutputs });
  });
  const edges = value.edges.map((edge) => validateEdgeInput(edge, inputs, outputs, nodes));
  return Object.freeze({
    id: validateVendorId(value.id), name: validateText(value.name, 120),
    version: validateVersion(value.version), sdkVersion: 1,
    description: validateText(value.description, 1_000), inputs, outputs,
    nodes: Object.freeze(nodes), edges: Object.freeze(edges),
  });
}

function validateDefinitionPorts(values) {
  if (!Array.isArray(values) || values.length > 8) throw invalid("Workflow ports are invalid.");
  const ids = new Set();
  return Object.freeze(values.map((item) => {
    exact(item, ["description", "id", "type"]);
    const id = validateLocalId(item.id);
    if (ids.has(id)) throw invalid("Workflow port identities must be unique.");
    ids.add(id);
    return Object.freeze({ id, type: validateValueType(item.type), description: validateText(item.description, 500) });
  }));
}

function definitionPortsMatch(actual, expected) {
  return actual.length === expected.length && actual.every((item, index) =>
    item.id === expected[index].portId && item.type === expected[index].valueType && item.description === expected[index].description);
}

function validateEdgeInput(value, inputs, outputs, nodes) {
  exact(value, ["source", "target"]);
  const source = validateEndpointInput(value.source, true, inputs, outputs, nodes);
  const target = validateEndpointInput(value.target, false, inputs, outputs, nodes);
  return Object.freeze({ source, target });
}

function validateEndpointInput(value, source, inputs, outputs, nodes) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw invalid("Workflow endpoint is invalid.");
  const keys = Object.keys(value).sort();
  if (source && keys.join() === "workflowInput") {
    const portId = validateLocalId(value.workflowInput);
    if (!inputs.some((portValue) => portValue.id === portId)) throw invalid("Workflow input endpoint is invalid.");
    return Object.freeze({ workflowInput: portId });
  }
  if (!source && keys.join() === "workflowOutput") {
    const portId = validateLocalId(value.workflowOutput);
    if (!outputs.some((portValue) => portValue.id === portId)) throw invalid("Workflow output endpoint is invalid.");
    return Object.freeze({ workflowOutput: portId });
  }
  if (keys.join() === "node,port") {
    const nodeId = validateLocalId(value.node);
    const portId = validateLocalId(value.port);
    const node = nodes.find((item) => item.id === nodeId);
    const ports = source ? node?.outputs : node?.inputs;
    if (!ports?.some((portValue) => portValue.id === portId)) throw invalid("Workflow node endpoint is invalid.");
    return Object.freeze({ node: nodeId, port: portId });
  }
  throw invalid("Workflow endpoint is invalid.");
}

function validateDefinitionView(value) {
  exact(value, ["schemaVersion", "workflow"]);
  if (value.schemaVersion !== 1) throw unavailable();
  const body = value.workflow;
  exact(body, ["description", "edges", "id", "inputs", "name", "nodes", "outputs", "sdkVersion", "version"]);
  const input = {
    schemaVersion: 1,
    workflow: {
      ...body,
      inputs: body.inputs,
      outputs: body.outputs,
      nodes: body.nodes,
      edges: body.edges.map((edge) => ({
        source: normalizedEndpointToInput(edge.source),
        target: normalizedEndpointToInput(edge.target),
      })),
    },
  };
  const validated = validateDefinitionInput(input);
  return Object.freeze({
    schemaVersion: 1,
    workflow: Object.freeze({
      ...validated.workflow,
      edges: Object.freeze(body.edges.map(validateNormalizedEdge)),
    }),
  });
}

function normalizedEndpointToInput(value) {
  exact(value, ["kind", "nodeId", "portId"]);
  if (value.kind === "workflow-input" && value.nodeId === null) return { workflowInput: value.portId };
  if (value.kind === "workflow-output" && value.nodeId === null) return { workflowOutput: value.portId };
  if (value.kind === "node" && typeof value.nodeId === "string") return { node: value.nodeId, port: value.portId };
  throw unavailable();
}

function validateNormalizedEdge(value) {
  exact(value, ["source", "target"]);
  return Object.freeze({ source: Object.freeze({ ...value.source }), target: Object.freeze({ ...value.target }) });
}

export function validatePlan(value, workflowId) {
  exact(value, ["plan"]);
  const plan = value.plan;
  exact(plan, ["failures", "steps", "summary", "valid", "version", "workflowId"]);
  validateText(plan.summary, 1_000);
  if (!Array.isArray(plan.steps) || !Array.isArray(plan.failures)) throw unavailable();
  if (plan.valid) {
    if (plan.workflowId !== workflowId || !VERSION.test(plan.version) || plan.steps.length < 1 || plan.steps.length > 8 || plan.failures.length) throw unavailable();
  } else if (plan.workflowId !== null || plan.version !== null || plan.steps.length || !plan.failures.length) throw unavailable();
  const steps = plan.steps.map((step, index) => {
    exact(step, ["dependencies", "nodeId", "operationId", "position"]);
    if (step.position !== index || !operationContract[step.operationId] || !Array.isArray(step.dependencies)) throw unavailable();
    return Object.freeze({ position: index, nodeId: validateLocalId(step.nodeId), operationId: step.operationId, dependencies: Object.freeze(step.dependencies.map(validateLocalId)) });
  });
  const failures = plan.failures.map((failure) => {
    exact(failure, ["code", "message", "nodeId", "operationId", "path"]);
    if (!PLAN_FAILURES.has(failure.code) || (failure.nodeId !== null && !LOCAL_ID.test(failure.nodeId)) || (failure.operationId !== null && !operationContract[failure.operationId])) throw unavailable();
    return Object.freeze({ ...failure, path: validateText(failure.path, 500), message: validateText(failure.message, 1_000) });
  });
  return Object.freeze({ plan: Object.freeze({ ...plan, steps: Object.freeze(steps), failures: Object.freeze(failures) }) });
}

export function validateExecution(value, workflowId, runId) {
  exact(value, ["execution"]);
  const execution = value.execution;
  exact(execution, ["completedStepCount", "failure", "outputs", "runId", "steps", "succeeded", "version", "workflowId"]);
  if (execution.runId !== runId || execution.workflowId !== workflowId || !VERSION.test(execution.version) || !Array.isArray(execution.outputs) || !Array.isArray(execution.steps) || execution.steps.length > 8 || execution.completedStepCount !== execution.steps.length || execution.succeeded !== (execution.failure === null)) throw unavailable();
  const outputs = Object.freeze(execution.outputs.map(validateRuntimeOutput));
  const steps = Object.freeze(execution.steps.map((step, index) => {
    exact(step, ["nodeId", "operationId", "outputs", "position"]);
    if (step.position !== index || !operationContract[step.operationId] || !Array.isArray(step.outputs)) throw unavailable();
    return Object.freeze({ ...step, nodeId: validateLocalId(step.nodeId), outputs: Object.freeze(step.outputs.map(validateRuntimeOutput)) });
  }));
  let failure = null;
  if (execution.failure !== null) {
    exact(execution.failure, ["code", "message", "nodeId", "operationId"]);
    if (!RUN_FAILURES.has(execution.failure.code) || (execution.failure.nodeId !== null && !LOCAL_ID.test(execution.failure.nodeId)) || (execution.failure.operationId !== null && !operationContract[execution.failure.operationId])) throw unavailable();
    failure = Object.freeze({ ...execution.failure, message: validateText(execution.failure.message, 1_000) });
  }
  return Object.freeze({ execution: Object.freeze({ ...execution, outputs, steps, failure }) });
}

function validateRuntimeOutput(value) {
  exact(value, ["portId", "value"]);
  validateRuntimeValue(value.value);
  return Object.freeze({ portId: validateLocalId(value.portId), value: structuredClone(value.value) });
}

function validateRuntimeValue(value) {
  let nodes = 0;
  const visit = (item, depth) => {
    nodes += 1;
    if (nodes > 4_096 || item === null || depth > 8) throw invalid("Workflow runtime value is invalid.");
    if (typeof item === "string") {
      if ([...item].length > 1_000) throw invalid("Workflow runtime text is too long.");
    } else if (typeof item === "number") {
      if (!Number.isFinite(item)) throw invalid("Workflow runtime number is invalid.");
    } else if (typeof item === "boolean") {
      return;
    } else if (Array.isArray(item)) {
      if (item.length > 256) throw invalid("Workflow runtime array is too large.");
      item.forEach((nested) => visit(nested, depth + 1));
    } else if (typeof item === "object") {
      const entries = Object.entries(item);
      if (entries.length > 256) throw invalid("Workflow runtime object is too large.");
      for (const [key, nested] of entries) {
        if (!key || key.trim() !== key || key.length > 128) throw invalid("Workflow runtime object key is invalid.");
        visit(nested, depth + 1);
      }
    } else throw invalid("Workflow runtime value is invalid.");
  };
  visit(value, 0);
  if (new TextEncoder().encode(JSON.stringify(value)).length > 6_000) throw invalid("Workflow runtime value is too large.");
}

function validateLocalId(value) {
  if (typeof value !== "string" || value.length > 64 || !LOCAL_ID.test(value)) throw invalid("Workflow local identifier is invalid.");
  return value;
}

function validateVendorId(value) {
  if (typeof value !== "string" || value.length > 128 || !VENDOR_ID.test(value)) throw invalid("Workflow identity is invalid.");
  return value;
}

function validateVersion(value) {
  if (typeof value !== "string" || value.length > 64 || !VERSION.test(value)) throw invalid("Workflow version is invalid.");
  return value;
}

function validateValueType(value) {
  if (typeof value !== "string" || !VALUE_TYPES.has(value)) throw invalid("Workflow value type is invalid.");
  return value;
}

function validateText(value, maximum) {
  if (typeof value !== "string" || !value.trim() || [...value.trim()].length > maximum) throw invalid("Workflow text is invalid.");
  return value.trim();
}

function requireConfirmation(value) {
  if (value !== true) throw invalid("Workflow operation requires confirmation.");
}

function exact(value, keys) {
  if (!value || typeof value !== "object" || Array.isArray(value) || Object.keys(value).sort().join() !== [...keys].sort().join()) throw unavailable();
}

function invalid(message) {
  return new BackendClientError("library.invalid_input", message);
}

function unavailable() {
  return new BackendClientError("backend.unavailable", "The local workflow service is unavailable.");
}
