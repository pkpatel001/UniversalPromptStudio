import "./workflow.css";
import {
  OFFLINE_REFERENCE_PROVIDER,
  OPENAI_RESPONSES_PROVIDER,
} from "./backend-client.js";
import {
  definitionViewToInput,
  PROMPT_WORKFLOW_OPERATION,
  WorkflowClient,
} from "./workflow-client.js";

const VALUE_TYPES = ["string", "integer", "number", "boolean", "object", "array"];

export function initializeWorkflowUI({ mount, backendClient, workflowClient = new WorkflowClient() }) {
  if (!(mount instanceof Element)) throw new TypeError("Workflow UI mount is invalid.");
  mount.insertAdjacentHTML("beforeend", markup());
  const root = mount.querySelector("#workflow-studio");
  const ui = createElements(root);
  const state = {
    workflows: [], operations: [], providers: [], projects: [], prompts: [],
    definition: null, persistedId: null, plan: null, execution: null,
  };

  const status = (kind, message) => {
    ui.status.dataset.state = kind;
    ui.status.textContent = message;
  };

  async function refreshCatalogs() {
    status("pending", "Opening the local workflow library…");
    try {
      const [operationResult, workflowResult, providerResult, projectResult] = await Promise.all([
        workflowClient.listOperations(), workflowClient.listWorkflows(),
        backendClient.listProviders(), backendClient.listProjects(),
      ]);
      state.operations = [...operationResult.operations];
      state.workflows = [...workflowResult.workflows];
      state.providers = [...providerResult.providers];
      state.projects = [...projectResult.projects];
      renderList();
      status("ready", `${state.workflows.length} workflow${state.workflows.length === 1 ? "" : "s"} saved locally.`);
    } catch (error) {
      status("error", error?.message ?? "The workflow library is unavailable.");
    }
  }

  function renderList() {
    ui.count.textContent = String(state.workflows.length);
    ui.list.replaceChildren();
    for (const workflow of state.workflows) {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.workflowId = workflow.workflowId;
      button.className = "workflow-list-item";
      if (workflow.workflowId === state.persistedId) button.classList.add("selected");
      const name = document.createElement("strong");
      name.textContent = workflow.name;
      const metadata = document.createElement("span");
      metadata.textContent = `${workflow.version} · ${workflow.nodeCount} nodes · ${workflow.edgeCount} edges`;
      button.append(name, metadata);
      ui.list.append(button);
    }
    if (!state.workflows.length) {
      const empty = document.createElement("p");
      empty.className = "workflow-empty-copy";
      empty.textContent = "Create the first bounded sequential workflow.";
      ui.list.append(empty);
    }
  }

  function openDefinition(definition, persistedId = null) {
    state.definition = definition;
    state.persistedId = persistedId;
    state.plan = null;
    state.execution = null;
    ui.empty.hidden = true;
    ui.editor.hidden = false;
    ui.id.disabled = Boolean(persistedId);
    ui.id.value = definition.workflow.id;
    ui.name.value = definition.workflow.name;
    ui.version.value = definition.workflow.version;
    ui.description.value = definition.workflow.description;
    renderList();
    renderPorts();
    renderNodes();
    renderEdges();
    renderRuntimeInputs();
    renderPlan();
    renderExecution();
  }

  function renderPorts() {
    renderPortGroup(ui.inputs, state.definition.workflow.inputs, "input");
    renderPortGroup(ui.outputs, state.definition.workflow.outputs, "output");
  }

  function renderPortGroup(container, ports, kind) {
    container.replaceChildren();
    ports.forEach((port, index) => {
      const row = document.createElement("div");
      row.className = "workflow-port-row";
      row.dataset.kind = kind;
      row.dataset.index = String(index);
      row.append(
        fieldInput("Port id", port.id, "id", 64),
        fieldSelect("Type", port.type, "type", VALUE_TYPES),
        fieldInput("Description", port.description, "description", 500),
        actionButton("Remove", "remove-port", "danger subtle"),
      );
      container.append(row);
    });
  }

  function renderNodes() {
    ui.nodes.replaceChildren();
    state.definition.workflow.nodes.forEach((node, index) => {
      const row = document.createElement("article");
      row.className = "workflow-node-card";
      row.dataset.index = String(index);
      const controls = document.createElement("div");
      controls.className = "workflow-node-controls";
      const idField = fieldInput("Node id", node.id, "node-id", 64);
      const operationField = fieldSelect(
        "Trusted operation", node.operation, "operation",
        state.operations.map((operation) => operation.operationId),
      );
      const actions = document.createElement("div");
      actions.className = "workflow-card-actions";
      actions.append(
        actionButton("↑", "node-up", "secondary", index === 0),
        actionButton("↓", "node-down", "secondary", index === state.definition.workflow.nodes.length - 1),
        actionButton("Delete", "delete-node", "danger subtle"),
      );
      controls.append(idField, operationField, actions);
      const contract = document.createElement("p");
      contract.className = "workflow-contract";
      contract.textContent = `Inputs: ${node.inputs.map((port) => `${port.id}:${port.type}`).join(", ") || "none"} · Outputs: ${node.outputs.map((port) => `${port.id}:${port.type}`).join(", ") || "none"}`;
      row.append(controls, contract);
      ui.nodes.append(row);
    });
  }

  function endpointOptions(source) {
    const values = [];
    if (source) {
      state.definition.workflow.inputs.forEach((port) => values.push({
        value: `workflow-input||${port.id}`, label: `Workflow input · ${port.id}`,
      }));
      state.definition.workflow.nodes.forEach((node) => node.outputs.forEach((port) => values.push({
        value: `node|${node.id}|${port.id}`, label: `${node.id} output · ${port.id}`,
      })));
    } else {
      state.definition.workflow.nodes.forEach((node) => node.inputs.forEach((port) => values.push({
        value: `node|${node.id}|${port.id}`, label: `${node.id} input · ${port.id}`,
      })));
      state.definition.workflow.outputs.forEach((port) => values.push({
        value: `workflow-output||${port.id}`, label: `Workflow output · ${port.id}`,
      }));
    }
    return values;
  }

  function renderEdges() {
    ui.edges.replaceChildren();
    state.definition.workflow.edges.forEach((edge, index) => {
      const row = document.createElement("div");
      row.className = "workflow-edge-row";
      const text = document.createElement("span");
      text.textContent = `${endpointLabel(edge.source)} → ${endpointLabel(edge.target)}`;
      const remove = actionButton("Remove", "remove-edge", "danger subtle");
      remove.dataset.index = String(index);
      row.append(text, remove);
      ui.edges.append(row);
    });
    const sources = endpointOptions(true);
    const targets = endpointOptions(false);
    fillSelect(ui.edgeSource, sources);
    fillSelect(ui.edgeTarget, targets);
    ui.addEdge.disabled = !sources.length || !targets.length;
  }

  function renderRuntimeInputs() {
    ui.runtimeInputs.replaceChildren();
    for (const port of state.definition.workflow.inputs) {
      let field;
      if (port.id === "provider-id") {
        field = selectField(port.id, state.providers.map((provider) => ({
          value: provider.providerId,
          label: `${provider.name}${provider.available ? "" : " · unavailable"}`,
          disabled: !provider.available,
        })));
      } else if (port.id === "project-id") {
        field = selectField(port.id, state.projects.map((project) => ({ value: project.projectId, label: project.name })));
        field.querySelector("select").dataset.runtimeProject = "true";
      } else if (port.id === "prompt-id") {
        field = selectField(port.id, state.prompts.map((prompt) => ({ value: prompt.promptId, label: prompt.title })));
      } else if (port.type === "boolean") {
        field = selectField(port.id, [{ value: "true", label: "true" }, { value: "false", label: "false" }]);
      } else {
        field = fieldInput(`${port.id} · ${port.type}`, "", "runtime-value", 1_000);
        field.querySelector("input").dataset.portType = port.type;
        field.querySelector("input").dataset.portId = port.id;
        if (["object", "array"].includes(port.type)) field.querySelector("input").placeholder = "Valid JSON";
      }
      const control = field.querySelector("select, input");
      control.dataset.portId = port.id;
      control.dataset.portType = port.type;
      ui.runtimeInputs.append(field);
    }
  }

  function renderPlan() {
    ui.plan.replaceChildren();
    ui.execute.disabled = !state.plan?.plan.valid;
    if (!state.plan) {
      ui.plan.textContent = "Save and validate this workflow to preview its deterministic order.";
      return;
    }
    const heading = document.createElement("strong");
    heading.textContent = state.plan.plan.valid ? "Execution plan ready" : "Workflow needs changes";
    ui.plan.append(heading);
    const list = document.createElement("ol");
    if (state.plan.plan.valid) {
      for (const step of state.plan.plan.steps) {
        const item = document.createElement("li");
        item.textContent = `${step.nodeId} · ${step.operationId}${step.dependencies.length ? ` · after ${step.dependencies.join(", ")}` : ""}`;
        list.append(item);
      }
    } else {
      for (const failure of state.plan.plan.failures) {
        const item = document.createElement("li");
        item.textContent = `${failure.path}: ${failure.message}`;
        list.append(item);
      }
    }
    ui.plan.append(list);
  }

  function renderExecution(pending = false) {
    ui.execution.hidden = !pending && !state.execution;
    ui.execution.replaceChildren();
    if (pending) {
      const title = document.createElement("strong");
      title.textContent = "Sequential run in progress";
      const list = document.createElement("ol");
      for (const step of state.plan.plan.steps) {
        const item = document.createElement("li");
        item.textContent = `${step.nodeId} · queued`;
        list.append(item);
      }
      ui.execution.append(title, list);
      return;
    }
    if (!state.execution) return;
    const run = state.execution.execution;
    const title = document.createElement("strong");
    title.textContent = run.succeeded ? "Workflow completed" : "Workflow stopped safely";
    const list = document.createElement("ol");
    for (const step of run.steps) {
      const item = document.createElement("li");
      item.textContent = `${step.nodeId} · completed · ${JSON.stringify(step.outputs.map((output) => output.value))}`;
      list.append(item);
    }
    const output = document.createElement("pre");
    output.textContent = run.succeeded
      ? JSON.stringify(Object.fromEntries(run.outputs.map((item) => [item.portId, item.value])), null, 2)
      : `${run.failure.code}: ${run.failure.message}`;
    ui.execution.append(title, list, output);
  }

  ui.newWorkflow.addEventListener("click", () => {
    const operation = state.operations.find((item) => item.operationId === "ups.echo-text");
    if (!operation) return;
    openDefinition(defaultDefinition(operation));
    status("ready", "New workflow draft created. Save it before planning.");
  });

  ui.list.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-workflow-id]");
    if (!button) return;
    status("pending", "Loading workflow definition…");
    try {
      const result = await workflowClient.getWorkflow(button.dataset.workflowId);
      openDefinition(definitionViewToInput(result.workflow), button.dataset.workflowId);
      status("ready", "Workflow loaded from local application data.");
    } catch (error) { status("error", error?.message ?? "Workflow could not be loaded."); }
  });

  ui.editor.addEventListener("input", (event) => {
    if (!state.definition) return;
    const target = event.target;
    if (target === ui.id) state.definition.workflow.id = target.value;
    else if (target === ui.name) state.definition.workflow.name = target.value;
    else if (target === ui.version) state.definition.workflow.version = target.value;
    else if (target === ui.description) state.definition.workflow.description = target.value;
    else if (target.closest(".workflow-port-row")) {
      const row = target.closest(".workflow-port-row");
      const ports = row.dataset.kind === "input" ? state.definition.workflow.inputs : state.definition.workflow.outputs;
      ports[Number(row.dataset.index)][target.dataset.field] = target.value;
    } else if (target.closest(".workflow-node-card")) {
      const row = target.closest(".workflow-node-card");
      const node = state.definition.workflow.nodes[Number(row.dataset.index)];
      if (target.dataset.field === "node-id") {
        const previous = node.id;
        node.id = target.value;
        state.definition.workflow.edges.forEach((edge) => {
          for (const endpoint of [edge.source, edge.target]) if (endpoint.node === previous) endpoint.node = target.value;
        });
        renderEdges();
      } else if (target.dataset.field === "operation") {
        node.operation = target.value;
        const operation = state.operations.find((item) => item.operationId === target.value);
        node.inputs = operation.inputs.map(operationPortDefinition);
        node.outputs = operation.outputs.map(operationPortDefinition);
        state.definition.workflow.edges = state.definition.workflow.edges.filter((edge) => edge.source.node !== node.id && edge.target.node !== node.id);
        renderNodes(); renderEdges();
      }
    }
    state.plan = null;
    renderPlan();
  });

  ui.editor.addEventListener("click", async (event) => {
    const action = event.target.dataset.action;
    if (!action || !state.definition) return;
    if (action === "add-input" || action === "add-output") {
      const ports = action === "add-input" ? state.definition.workflow.inputs : state.definition.workflow.outputs;
      if (ports.length < 8) ports.push({ id: uniqueId(action === "add-input" ? "input" : "output", ports), type: "string", description: "Workflow value." });
      renderPorts(); renderEdges(); renderRuntimeInputs();
    } else if (action === "remove-port") {
      const row = event.target.closest(".workflow-port-row");
      const ports = row.dataset.kind === "input" ? state.definition.workflow.inputs : state.definition.workflow.outputs;
      const removed = ports.splice(Number(row.dataset.index), 1)[0];
      state.definition.workflow.edges = state.definition.workflow.edges.filter((edge) =>
        row.dataset.kind === "input" ? edge.source.workflowInput !== removed.id : edge.target.workflowOutput !== removed.id);
      renderPorts(); renderEdges(); renderRuntimeInputs();
    } else if (action === "add-node") {
      if (state.definition.workflow.nodes.length >= 8) return;
      const operation = state.operations[0];
      state.definition.workflow.nodes.push({
        id: uniqueId("step", state.definition.workflow.nodes), operation: operation.operationId,
        inputs: operation.inputs.map(operationPortDefinition), outputs: operation.outputs.map(operationPortDefinition),
      });
      renderNodes(); renderEdges();
    } else if (["node-up", "node-down", "delete-node"].includes(action)) {
      const index = Number(event.target.closest(".workflow-node-card").dataset.index);
      const nodes = state.definition.workflow.nodes;
      if (action === "delete-node") {
        const [removed] = nodes.splice(index, 1);
        state.definition.workflow.edges = state.definition.workflow.edges.filter((edge) => edge.source.node !== removed.id && edge.target.node !== removed.id);
      } else {
        const target = action === "node-up" ? index - 1 : index + 1;
        [nodes[index], nodes[target]] = [nodes[target], nodes[index]];
      }
      renderNodes(); renderEdges();
    } else if (action === "remove-edge") {
      state.definition.workflow.edges.splice(Number(event.target.dataset.index), 1);
      renderEdges();
    }
    state.plan = null;
    renderPlan();
  });

  ui.addEdge.addEventListener("click", () => {
    state.definition.workflow.edges.push({ source: parseEndpoint(ui.edgeSource.value), target: parseEndpoint(ui.edgeTarget.value) });
    state.plan = null; renderEdges(); renderPlan();
  });

  ui.save.addEventListener("click", async () => {
    status("pending", "Validating and saving the workflow definition…");
    try {
      const result = state.persistedId
        ? await workflowClient.updateWorkflow(state.persistedId, state.definition)
        : await workflowClient.createWorkflow(state.definition);
      const id = result.workflow.workflow.id;
      openDefinition(definitionViewToInput(result.workflow), id);
      await refreshCatalogs();
      status("ready", "Workflow definition saved atomically below application data.");
    } catch (error) { status("error", error?.message ?? "Workflow could not be saved."); }
  });

  ui.planButton.addEventListener("click", async () => {
    if (!state.persistedId) { status("error", "Save the workflow before validating its plan."); return; }
    status("pending", "Validating graph and building the deterministic plan…");
    try {
      state.plan = await workflowClient.planWorkflow(state.persistedId);
      renderPlan();
      status(state.plan.plan.valid ? "ready" : "error", state.plan.plan.summary);
    } catch (error) { status("error", error?.message ?? "Workflow planning failed safely."); }
  });

  ui.deleteButton.addEventListener("click", async () => {
    if (!state.persistedId || !window.confirm(`Delete ${state.persistedId}?`)) return;
    try {
      await workflowClient.deleteWorkflow(state.persistedId, true);
      state.definition = null; state.persistedId = null; ui.editor.hidden = true; ui.empty.hidden = false;
      await refreshCatalogs();
      status("ready", "Workflow deleted from local application data.");
    } catch (error) { status("error", error?.message ?? "Workflow could not be deleted."); }
  });

  ui.runtimeInputs.addEventListener("change", async (event) => {
    if (event.target.dataset.runtimeProject !== "true") return;
    try {
      state.prompts = [...(await backendClient.listPrompts(event.target.value)).prompts];
      renderRuntimeInputs();
      const project = ui.runtimeInputs.querySelector('[data-port-id="project-id"]');
      if (project) project.value = event.target.value;
    } catch (error) { status("error", error?.message ?? "Project prompts are unavailable."); }
  });

  ui.execute.addEventListener("click", async () => {
    if (!state.plan?.plan.valid || !state.persistedId || !window.confirm(`Run ${state.plan.plan.steps.length} steps sequentially?`)) return;
    try {
      const inputs = [...ui.runtimeInputs.querySelectorAll("[data-port-id]")].map(runtimeInput);
      status("pending", "Running each planned operation once, in order…");
      renderExecution(true);
      state.execution = await workflowClient.executeWorkflow(state.persistedId, inputs, true);
      renderExecution();
      status(state.execution.execution.succeeded ? "ready" : "error", state.execution.execution.succeeded ? "Workflow completed successfully." : "Workflow stopped safely at the failing step.");
    } catch (error) { state.execution = null; renderExecution(); status("error", error?.message ?? "Workflow execution failed safely."); }
  });

  void refreshCatalogs();
  return Object.freeze({
    refresh: refreshCatalogs,
    selectedWorkflow: () => {
      if (!state.persistedId) return null;
      return Object.freeze({
        workflowId: state.persistedId,
        name: state.workflows.find((item) => item.workflowId === state.persistedId)?.name ?? state.definition?.workflow.name ?? state.persistedId,
      });
    },
  });
}

function markup() {
  return `<section id="workflow-studio" class="workflow-studio" aria-labelledby="workflow-heading">
    <div class="workflow-header"><div><p>Schema-1 workflow studio</p><h2 id="workflow-heading">Author, validate, and run sequential workflows</h2></div><button id="workflow-new" class="primary" type="button">New workflow</button></div>
    <div id="workflow-status" class="library-status" data-state="pending" role="status" aria-live="polite">Opening workflows…</div>
    <div class="workflow-layout"><aside class="workflow-browser"><div class="section-heading"><h3>Workflows</h3><span id="workflow-count">0</span></div><div id="workflow-list"></div></aside>
    <section class="workflow-editor"><div id="workflow-empty" class="empty-state"><strong>Select or create a workflow</strong><span>Definitions stay local and use only trusted host operations.</span></div>
    <div id="workflow-editor" hidden><div class="workflow-editor-actions"><button id="workflow-delete" class="danger subtle" type="button">Delete</button><button id="workflow-save" class="secondary" type="button">Save definition</button><button id="workflow-plan-button" class="primary" type="button">Validate &amp; preview plan</button></div>
    <div class="workflow-metadata"><label>Workflow id<input id="workflow-id" maxlength="128"></label><label>Name<input id="workflow-name" maxlength="120"></label><label>Version<input id="workflow-version" maxlength="64"></label><label class="wide">Description<textarea id="workflow-description" maxlength="1000"></textarea></label></div>
    <div class="workflow-columns"><section><div class="block-heading"><div><h4>Workflow inputs</h4><p>Typed values supplied at run time.</p></div><button data-action="add-input" class="secondary" type="button">Add input</button></div><div id="workflow-inputs"></div></section><section><div class="block-heading"><div><h4>Workflow outputs</h4><p>Typed final values.</p></div><button data-action="add-output" class="secondary" type="button">Add output</button></div><div id="workflow-outputs"></div></section></div>
    <section><div class="block-heading"><div><h4>Ordered node presentation</h4><p>Planning derives deterministic execution order from edges.</p></div><button data-action="add-node" class="secondary" type="button">Add trusted node</button></div><div id="workflow-nodes"></div></section>
    <section><div class="block-heading"><div><h4>Directed edges</h4><p>Cycles and duplicate targets are rejected during planning.</p></div></div><div id="workflow-edges"></div><div class="workflow-edge-builder"><select id="workflow-edge-source"></select><span>→</span><select id="workflow-edge-target"></select><button id="workflow-add-edge" class="secondary" type="button">Add edge</button></div></section>
    <section class="workflow-runtime"><div class="runtime-heading"><div><p>Confirmed sequential execution</p><h4>Inputs, plan, progress, and result</h4></div><span class="offline-badge">No background runs</span></div><div id="workflow-runtime-inputs" class="workflow-runtime-inputs"></div><div id="workflow-plan" class="workflow-plan"></div><button id="workflow-execute" class="primary" type="button" disabled>Run planned workflow</button><div id="workflow-execution" class="runtime-output" hidden></div></section>
    </div></section></div></section>`;
}

function createElements(root) {
  const get = (id) => root.querySelector(`#${id}`);
  return {
    status: get("workflow-status"), count: get("workflow-count"), list: get("workflow-list"),
    newWorkflow: get("workflow-new"), empty: get("workflow-empty"), editor: get("workflow-editor"),
    id: get("workflow-id"), name: get("workflow-name"), version: get("workflow-version"),
    description: get("workflow-description"), inputs: get("workflow-inputs"), outputs: get("workflow-outputs"),
    nodes: get("workflow-nodes"), edges: get("workflow-edges"), edgeSource: get("workflow-edge-source"),
    edgeTarget: get("workflow-edge-target"), addEdge: get("workflow-add-edge"), save: get("workflow-save"),
    planButton: get("workflow-plan-button"), deleteButton: get("workflow-delete"), plan: get("workflow-plan"),
    runtimeInputs: get("workflow-runtime-inputs"), execute: get("workflow-execute"), execution: get("workflow-execution"),
  };
}

function defaultDefinition(operation) {
  return { schemaVersion: 1, workflow: {
    id: `ups.user-flow-${Date.now().toString(36)}`, name: "Untitled workflow", version: "1.0.0", sdkVersion: 1,
    description: "Bounded local sequential workflow.",
    inputs: [{ id: "input", type: "string", description: "Workflow text input." }],
    outputs: [{ id: "output", type: "string", description: "Workflow text output." }],
    nodes: [{ id: "step", operation: operation.operationId, inputs: operation.inputs.map(operationPortDefinition), outputs: operation.outputs.map(operationPortDefinition) }],
    edges: [
      { source: { workflowInput: "input" }, target: { node: "step", port: operation.inputs[0].portId } },
      { source: { node: "step", port: operation.outputs[0].portId }, target: { workflowOutput: "output" } },
    ],
  } };
}

function operationPortDefinition(value) { return { id: value.portId, type: value.valueType, description: value.description }; }
function fieldInput(labelText, value, field, maximum) { const label = document.createElement("label"); label.textContent = labelText; const input = document.createElement("input"); input.value = value; input.maxLength = maximum; input.dataset.field = field; label.append(input); return label; }
function fieldSelect(labelText, value, field, values) { const label = document.createElement("label"); label.textContent = labelText; const select = document.createElement("select"); select.dataset.field = field; fillSelect(select, values.map((item) => ({ value: item, label: item }))); select.value = value; label.append(select); return label; }
function selectField(labelText, values) { const label = document.createElement("label"); label.textContent = labelText; const select = document.createElement("select"); fillSelect(select, values); label.append(select); return label; }
function actionButton(text, action, className, disabled = false) { const button = document.createElement("button"); button.type = "button"; button.textContent = text; button.dataset.action = action; button.className = className; button.disabled = disabled; return button; }
function fillSelect(select, values) { select.replaceChildren(); for (const value of values) { const option = document.createElement("option"); option.value = value.value; option.textContent = value.label; option.disabled = Boolean(value.disabled); select.append(option); } }
function parseEndpoint(value) { const [kind, node, port] = value.split("|"); if (kind === "workflow-input") return { workflowInput: port }; if (kind === "workflow-output") return { workflowOutput: port }; return { node, port }; }
function endpointLabel(endpoint) { if (endpoint.workflowInput) return `input.${endpoint.workflowInput}`; if (endpoint.workflowOutput) return `output.${endpoint.workflowOutput}`; return `${endpoint.node}.${endpoint.port}`; }
function uniqueId(prefix, values) { const ids = new Set(values.map((value) => value.id)); let index = values.length + 1; while (ids.has(`${prefix}-${index}`)) index += 1; return `${prefix}-${index}`; }
function runtimeInput(control) { let value = control.value; const type = control.dataset.portType; if (type === "integer") { value = Number(value); if (!Number.isSafeInteger(value)) throw new Error(`${control.dataset.portId} must be an integer.`); } else if (type === "number") { value = Number(value); if (!Number.isFinite(value)) throw new Error(`${control.dataset.portId} must be a number.`); } else if (type === "boolean") value = value === "true"; else if (["object", "array"].includes(type)) value = JSON.parse(value); return { portId: control.dataset.portId, value }; }
