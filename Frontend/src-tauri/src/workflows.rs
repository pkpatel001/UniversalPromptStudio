//! Typed A-005 workflow bridge with independent desktop-side validation.

use crate::backend::{BackendCommandError, BackendManager};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeSet;
use std::time::Duration;

const WORKFLOW_OPERATIONS_COMMAND: &str = "workflows.operations.list";
const WORKFLOW_LIST_COMMAND: &str = "workflows.list";
const WORKFLOW_CREATE_COMMAND: &str = "workflows.create";
const WORKFLOW_GET_COMMAND: &str = "workflows.get";
const WORKFLOW_UPDATE_COMMAND: &str = "workflows.update";
const WORKFLOW_DELETE_COMMAND: &str = "workflows.delete";
const WORKFLOW_PLAN_COMMAND: &str = "workflows.plan";
const WORKFLOW_EXECUTE_COMMAND: &str = "workflows.execute";
const WORKFLOW_RESPONSE_TIMEOUT: Duration = Duration::from_secs(35);
const MAX_WORKFLOWS: usize = 50;
const MAX_WORKFLOW_PORTS: usize = 8;
const MAX_WORKFLOW_NODES: usize = 8;
const MAX_WORKFLOW_EDGES: usize = 64;
const MAX_WORKFLOW_RUNTIME_STRING_LENGTH: usize = 1_000;
const MAX_WORKFLOW_RUNTIME_VALUE_BYTES: usize = 6_000;
const PROMPT_OPERATION: &str = "ups.execute-saved-prompt";

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowOperationCatalog {
    operations: Vec<WorkflowOperation>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowOperation {
    operation_id: String,
    sdk_version: u32,
    inputs: Vec<WorkflowOperationPort>,
    outputs: Vec<WorkflowOperationPort>,
    requires_provider: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowOperationPort {
    port_id: String,
    value_type: String,
    description: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowList {
    workflows: Vec<WorkflowSummary>,
    has_more: bool,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowSummary {
    workflow_id: String,
    name: String,
    version: String,
    description: String,
    node_count: usize,
    edge_count: usize,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowDefinitionResult {
    workflow: WorkflowDefinitionView,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DeletedWorkflow {
    deleted_workflow_id: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowPlanResult {
    plan: WorkflowPlan,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowPlan {
    valid: bool,
    summary: String,
    workflow_id: Option<String>,
    version: Option<String>,
    steps: Vec<WorkflowPlanStep>,
    failures: Vec<WorkflowPlanFailure>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowPlanStep {
    position: usize,
    node_id: String,
    operation_id: String,
    dependencies: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowPlanFailure {
    code: String,
    path: String,
    message: String,
    node_id: Option<String>,
    operation_id: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowExecutionResult {
    execution: WorkflowExecution,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowExecution {
    run_id: String,
    workflow_id: String,
    version: String,
    succeeded: bool,
    completed_step_count: usize,
    outputs: Vec<WorkflowRuntimeValueView>,
    steps: Vec<WorkflowExecutionStep>,
    failure: Option<WorkflowExecutionFailure>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowExecutionStep {
    position: usize,
    node_id: String,
    operation_id: String,
    outputs: Vec<WorkflowRuntimeValueView>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowExecutionFailure {
    code: String,
    message: String,
    node_id: Option<String>,
    operation_id: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowRuntimeValueView {
    port_id: String,
    value: Value,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowDefinitionView {
    schema_version: u32,
    workflow: WorkflowBodyView,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowBodyView {
    id: String,
    name: String,
    version: String,
    sdk_version: u32,
    description: String,
    inputs: Vec<WorkflowPortView>,
    outputs: Vec<WorkflowPortView>,
    nodes: Vec<WorkflowNodeView>,
    edges: Vec<WorkflowEdgeView>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowPortView {
    id: String,
    #[serde(rename = "type")]
    value_type: String,
    description: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowNodeView {
    id: String,
    operation: String,
    inputs: Vec<WorkflowPortView>,
    outputs: Vec<WorkflowPortView>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowEdgeView {
    source: WorkflowEndpointView,
    target: WorkflowEndpointView,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkflowEndpointView {
    kind: String,
    port_id: String,
    node_id: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(
    deny_unknown_fields,
    rename_all(deserialize = "camelCase", serialize = "snake_case")
)]
pub struct WorkflowDefinitionInput {
    schema_version: u32,
    workflow: WorkflowBodyInput,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(
    deny_unknown_fields,
    rename_all(deserialize = "camelCase", serialize = "snake_case")
)]
struct WorkflowBodyInput {
    id: String,
    name: String,
    version: String,
    sdk_version: u32,
    description: String,
    inputs: Vec<WorkflowPortInput>,
    outputs: Vec<WorkflowPortInput>,
    nodes: Vec<WorkflowNodeInput>,
    edges: Vec<WorkflowEdgeInput>,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct WorkflowPortInput {
    id: String,
    #[serde(rename = "type")]
    value_type: String,
    description: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct WorkflowNodeInput {
    id: String,
    operation: String,
    inputs: Vec<WorkflowPortInput>,
    outputs: Vec<WorkflowPortInput>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct WorkflowEdgeInput {
    source: WorkflowEndpointInput,
    target: WorkflowEndpointInput,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(untagged)]
enum WorkflowEndpointInput {
    WorkflowInput(WorkflowInputEndpoint),
    WorkflowOutput(WorkflowOutputEndpoint),
    Node(NodeEndpoint),
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(
    deny_unknown_fields,
    rename_all(deserialize = "camelCase", serialize = "snake_case")
)]
struct WorkflowInputEndpoint {
    workflow_input: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(
    deny_unknown_fields,
    rename_all(deserialize = "camelCase", serialize = "snake_case")
)]
struct WorkflowOutputEndpoint {
    workflow_output: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct NodeEndpoint {
    node: String,
    port: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(
    deny_unknown_fields,
    rename_all(deserialize = "camelCase", serialize = "snake_case")
)]
pub struct WorkflowRuntimeInput {
    port_id: String,
    value: Value,
}

#[derive(Debug, Serialize)]
struct EmptyPayload {}

#[derive(Debug, Serialize)]
struct WorkflowIdPayload<'a> {
    workflow_id: &'a str,
}

#[derive(Debug, Serialize)]
struct WorkflowPayload<'a> {
    workflow: &'a WorkflowDefinitionInput,
}

#[derive(Debug, Serialize)]
struct WorkflowUpdatePayload<'a> {
    workflow_id: &'a str,
    workflow: &'a WorkflowDefinitionInput,
}

#[derive(Debug, Serialize)]
struct WorkflowDeletePayload<'a> {
    workflow_id: &'a str,
    confirm: bool,
}

#[derive(Debug, Serialize)]
struct WorkflowExecutePayload<'a> {
    workflow_id: &'a str,
    run_id: &'a str,
    inputs: &'a [WorkflowRuntimeInput],
    confirm: bool,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireOperationCatalog {
    operations: Vec<WireOperation>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireOperation {
    operation_id: String,
    sdk_version: u32,
    inputs: Vec<WireOperationPort>,
    outputs: Vec<WireOperationPort>,
    requires_provider: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireOperationPort {
    port_id: String,
    value_type: String,
    description: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireWorkflowList {
    workflows: Vec<WireWorkflowSummary>,
    has_more: bool,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireWorkflowSummary {
    workflow_id: String,
    name: String,
    version: String,
    description: String,
    node_count: usize,
    edge_count: usize,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireDefinitionResult {
    workflow: WireDefinition,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireDeletedWorkflow {
    deleted_workflow_id: String,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireDefinition {
    schema_version: u32,
    workflow: WireWorkflowBody,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireWorkflowBody {
    id: String,
    name: String,
    version: String,
    sdk_version: u32,
    description: String,
    inputs: Vec<WireDefinitionPort>,
    outputs: Vec<WireDefinitionPort>,
    nodes: Vec<WireNode>,
    edges: Vec<WireEdge>,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireDefinitionPort {
    id: String,
    #[serde(rename = "type")]
    value_type: String,
    description: String,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireNode {
    id: String,
    operation: String,
    inputs: Vec<WireDefinitionPort>,
    outputs: Vec<WireDefinitionPort>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireEdge {
    source: WireEndpoint,
    target: WireEndpoint,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(untagged)]
enum WireEndpoint {
    WorkflowInput(WireWorkflowInputEndpoint),
    WorkflowOutput(WireWorkflowOutputEndpoint),
    Node(WireNodeEndpoint),
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireWorkflowInputEndpoint {
    workflow_input: String,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireWorkflowOutputEndpoint {
    workflow_output: String,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireNodeEndpoint {
    node: String,
    port: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WirePlanResult {
    plan: WirePlan,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WirePlan {
    valid: bool,
    summary: String,
    workflow_id: Option<String>,
    version: Option<String>,
    steps: Vec<WirePlanStep>,
    failures: Vec<WirePlanFailure>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WirePlanStep {
    position: usize,
    node_id: String,
    operation_id: String,
    dependencies: Vec<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WirePlanFailure {
    code: String,
    path: String,
    message: String,
    node_id: Option<String>,
    operation_id: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireExecutionResult {
    execution: WireExecution,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireExecution {
    run_id: String,
    workflow_id: String,
    version: String,
    succeeded: bool,
    completed_step_count: usize,
    outputs: Vec<WireRuntimeValue>,
    steps: Vec<WireExecutionStep>,
    failure: Option<WireExecutionFailure>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireRuntimeValue {
    port_id: String,
    value: Value,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireExecutionStep {
    position: usize,
    node_id: String,
    operation_id: String,
    outputs: Vec<WireRuntimeValue>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireExecutionFailure {
    code: String,
    message: String,
    node_id: Option<String>,
    operation_id: Option<String>,
}

#[tauri::command]
pub async fn workflow_operations(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
) -> Result<WorkflowOperationCatalog, BackendCommandError> {
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireOperationCatalog =
            manager.request(&request_id, WORKFLOW_OPERATIONS_COMMAND, EmptyPayload {})?;
        validate_operation_catalog(wire)
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn workflows(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
) -> Result<WorkflowList, BackendCommandError> {
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireWorkflowList =
            manager.request(&request_id, WORKFLOW_LIST_COMMAND, EmptyPayload {})?;
        validate_workflow_list(wire)
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn workflow_create(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    workflow: WorkflowDefinitionInput,
) -> Result<WorkflowDefinitionResult, BackendCommandError> {
    validate_definition_input(&workflow)?;
    let expected_id = workflow.workflow.id.clone();
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireDefinitionResult = manager.request(
            &request_id,
            WORKFLOW_CREATE_COMMAND,
            WorkflowPayload {
                workflow: &workflow,
            },
        )?;
        validate_definition_result(wire, Some(&expected_id))
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn workflow_get(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    workflow_id: String,
) -> Result<WorkflowDefinitionResult, BackendCommandError> {
    validate_vendor_id(&workflow_id)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireDefinitionResult = manager.request(
            &request_id,
            WORKFLOW_GET_COMMAND,
            WorkflowIdPayload {
                workflow_id: &workflow_id,
            },
        )?;
        validate_definition_result(wire, Some(&workflow_id))
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn workflow_update(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    workflow_id: String,
    workflow: WorkflowDefinitionInput,
) -> Result<WorkflowDefinitionResult, BackendCommandError> {
    validate_vendor_id(&workflow_id)?;
    validate_definition_input(&workflow)?;
    if workflow.workflow.id != workflow_id {
        return Err(BackendCommandError::invalid_request(
            "Workflow identity cannot change during update.",
        ));
    }
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireDefinitionResult = manager.request(
            &request_id,
            WORKFLOW_UPDATE_COMMAND,
            WorkflowUpdatePayload {
                workflow_id: &workflow_id,
                workflow: &workflow,
            },
        )?;
        validate_definition_result(wire, Some(&workflow_id))
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn workflow_delete(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    workflow_id: String,
    confirm: bool,
) -> Result<DeletedWorkflow, BackendCommandError> {
    validate_vendor_id(&workflow_id)?;
    validate_confirmation(confirm)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireDeletedWorkflow = manager.request(
            &request_id,
            WORKFLOW_DELETE_COMMAND,
            WorkflowDeletePayload {
                workflow_id: &workflow_id,
                confirm,
            },
        )?;
        if wire.deleted_workflow_id != workflow_id {
            return Err(BackendCommandError::unavailable());
        }
        Ok(DeletedWorkflow {
            deleted_workflow_id: wire.deleted_workflow_id,
        })
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn workflow_plan(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    workflow_id: String,
) -> Result<WorkflowPlanResult, BackendCommandError> {
    validate_vendor_id(&workflow_id)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WirePlanResult = manager.request(
            &request_id,
            WORKFLOW_PLAN_COMMAND,
            WorkflowIdPayload {
                workflow_id: &workflow_id,
            },
        )?;
        validate_plan(wire, &workflow_id)
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn workflow_execute(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    workflow_id: String,
    run_id: String,
    inputs: Vec<WorkflowRuntimeInput>,
    confirm: bool,
) -> Result<WorkflowExecutionResult, BackendCommandError> {
    validate_vendor_id(&workflow_id)?;
    validate_uuid(&run_id)?;
    validate_confirmation(confirm)?;
    validate_runtime_inputs(&inputs)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireExecutionResult = manager.request_with_timeout(
            &request_id,
            WORKFLOW_EXECUTE_COMMAND,
            WorkflowExecutePayload {
                workflow_id: &workflow_id,
                run_id: &run_id,
                inputs: &inputs,
                confirm,
            },
            WORKFLOW_RESPONSE_TIMEOUT,
        )?;
        validate_execution(wire, &workflow_id, &run_id)
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

fn validate_operation_catalog(
    wire: WireOperationCatalog,
) -> Result<WorkflowOperationCatalog, BackendCommandError> {
    let expected_ids = ["ups.echo-text", PROMPT_OPERATION, "ups.uppercase-text"];
    if wire.operations.len() != expected_ids.len() {
        return Err(BackendCommandError::unavailable());
    }
    let mut operations = Vec::with_capacity(wire.operations.len());
    for (operation, expected_id) in wire.operations.into_iter().zip(expected_ids) {
        if operation.operation_id != expected_id
            || operation.sdk_version != 1
            || operation.requires_provider != (expected_id == PROMPT_OPERATION)
        {
            return Err(BackendCommandError::unavailable());
        }
        let (inputs, outputs) =
            expected_operation_ports(expected_id).ok_or_else(BackendCommandError::unavailable)?;
        if operation.inputs != inputs || operation.outputs != outputs {
            return Err(BackendCommandError::unavailable());
        }
        operations.push(WorkflowOperation {
            operation_id: operation.operation_id,
            sdk_version: operation.sdk_version,
            inputs: operation
                .inputs
                .into_iter()
                .map(operation_port_view)
                .collect(),
            outputs: operation
                .outputs
                .into_iter()
                .map(operation_port_view)
                .collect(),
            requires_provider: operation.requires_provider,
        });
    }
    Ok(WorkflowOperationCatalog { operations })
}

fn validate_workflow_list(wire: WireWorkflowList) -> Result<WorkflowList, BackendCommandError> {
    if wire.workflows.len() > MAX_WORKFLOWS || wire.has_more {
        return Err(BackendCommandError::unavailable());
    }
    let mut ids = BTreeSet::new();
    let mut workflows = Vec::with_capacity(wire.workflows.len());
    for item in wire.workflows {
        validate_vendor_id(&item.workflow_id).map_err(|_| BackendCommandError::unavailable())?;
        validate_text(&item.name, 120, false)?;
        validate_version(&item.version)?;
        validate_text(&item.description, 1_000, false)?;
        if item.node_count == 0
            || item.node_count > MAX_WORKFLOW_NODES
            || item.edge_count > MAX_WORKFLOW_EDGES
            || !ids.insert(item.workflow_id.clone())
        {
            return Err(BackendCommandError::unavailable());
        }
        workflows.push(WorkflowSummary {
            workflow_id: item.workflow_id,
            name: item.name,
            version: item.version,
            description: item.description,
            node_count: item.node_count,
            edge_count: item.edge_count,
        });
    }
    if workflows
        .windows(2)
        .any(|pair| pair[0].workflow_id >= pair[1].workflow_id)
    {
        return Err(BackendCommandError::unavailable());
    }
    Ok(WorkflowList {
        workflows,
        has_more: false,
    })
}

fn validate_definition_input(value: &WorkflowDefinitionInput) -> Result<(), BackendCommandError> {
    let wire = WireDefinition {
        schema_version: value.schema_version,
        workflow: WireWorkflowBody {
            id: value.workflow.id.clone(),
            name: value.workflow.name.clone(),
            version: value.workflow.version.clone(),
            sdk_version: value.workflow.sdk_version,
            description: value.workflow.description.clone(),
            inputs: value.workflow.inputs.iter().map(input_port_wire).collect(),
            outputs: value.workflow.outputs.iter().map(input_port_wire).collect(),
            nodes: value
                .workflow
                .nodes
                .iter()
                .map(|node| WireNode {
                    id: node.id.clone(),
                    operation: node.operation.clone(),
                    inputs: node.inputs.iter().map(input_port_wire).collect(),
                    outputs: node.outputs.iter().map(input_port_wire).collect(),
                })
                .collect(),
            edges: value.workflow.edges.iter().map(input_edge_wire).collect(),
        },
    };
    validate_definition(wire).map(|_| ())
}

fn validate_definition_result(
    wire: WireDefinitionResult,
    expected_id: Option<&str>,
) -> Result<WorkflowDefinitionResult, BackendCommandError> {
    let workflow = validate_definition(wire.workflow)?;
    if expected_id.is_some_and(|expected| workflow.workflow.id != expected) {
        return Err(BackendCommandError::unavailable());
    }
    Ok(WorkflowDefinitionResult { workflow })
}

fn validate_definition(
    value: WireDefinition,
) -> Result<WorkflowDefinitionView, BackendCommandError> {
    let workflow = &value.workflow;
    if value.schema_version != 1
        || workflow.sdk_version != 1
        || workflow.inputs.len() > MAX_WORKFLOW_PORTS
        || workflow.outputs.len() > MAX_WORKFLOW_PORTS
        || !(1..=MAX_WORKFLOW_NODES).contains(&workflow.nodes.len())
        || workflow.edges.len() > MAX_WORKFLOW_EDGES
    {
        return Err(BackendCommandError::invalid_request(
            "Workflow definition is invalid.",
        ));
    }
    validate_vendor_id(&workflow.id)?;
    validate_text(&workflow.name, 120, false)?;
    validate_version(&workflow.version)?;
    validate_text(&workflow.description, 1_000, false)?;
    validate_definition_ports(&workflow.inputs)?;
    validate_definition_ports(&workflow.outputs)?;
    let mut node_ids = BTreeSet::new();
    for node in &workflow.nodes {
        validate_local_id(&node.id)?;
        if !node_ids.insert(node.id.clone()) {
            return Err(BackendCommandError::invalid_request(
                "Workflow node identities must be unique.",
            ));
        }
        let (expected_inputs, expected_outputs) = expected_definition_ports(&node.operation)
            .ok_or_else(|| {
                BackendCommandError::invalid_request("Workflow operation is not authorized.")
            })?;
        if node.inputs != expected_inputs || node.outputs != expected_outputs {
            return Err(BackendCommandError::invalid_request(
                "Workflow node ports do not match the trusted operation.",
            ));
        }
    }
    for edge in &workflow.edges {
        validate_wire_endpoint(&edge.source, true, workflow)?;
        validate_wire_endpoint(&edge.target, false, workflow)?;
    }
    let view = WorkflowDefinitionView {
        schema_version: value.schema_version,
        workflow: WorkflowBodyView {
            id: workflow.id.clone(),
            name: workflow.name.clone(),
            version: workflow.version.clone(),
            sdk_version: workflow.sdk_version,
            description: workflow.description.clone(),
            inputs: workflow.inputs.iter().map(definition_port_view).collect(),
            outputs: workflow.outputs.iter().map(definition_port_view).collect(),
            nodes: workflow
                .nodes
                .iter()
                .map(|node| WorkflowNodeView {
                    id: node.id.clone(),
                    operation: node.operation.clone(),
                    inputs: node.inputs.iter().map(definition_port_view).collect(),
                    outputs: node.outputs.iter().map(definition_port_view).collect(),
                })
                .collect(),
            edges: workflow
                .edges
                .iter()
                .map(|edge| WorkflowEdgeView {
                    source: endpoint_view(&edge.source),
                    target: endpoint_view(&edge.target),
                })
                .collect(),
        },
    };
    let encoded = serde_json::to_vec(&view).map_err(|_| BackendCommandError::unavailable())?;
    if encoded.len() > 12_000 {
        return Err(BackendCommandError::invalid_request(
            "Workflow definition is too large.",
        ));
    }
    Ok(view)
}

fn validate_plan(
    wire: WirePlanResult,
    expected_id: &str,
) -> Result<WorkflowPlanResult, BackendCommandError> {
    validate_text(&wire.plan.summary, 1_000, false)?;
    if wire.plan.valid {
        if wire.plan.workflow_id.as_deref() != Some(expected_id)
            || wire.plan.version.is_none()
            || wire.plan.steps.is_empty()
            || wire.plan.steps.len() > MAX_WORKFLOW_NODES
            || !wire.plan.failures.is_empty()
        {
            return Err(BackendCommandError::unavailable());
        }
    } else if wire.plan.workflow_id.is_some()
        || wire.plan.version.is_some()
        || !wire.plan.steps.is_empty()
        || wire.plan.failures.is_empty()
    {
        return Err(BackendCommandError::unavailable());
    }
    if let Some(version) = &wire.plan.version {
        validate_version(version).map_err(|_| BackendCommandError::unavailable())?;
    }
    let steps = wire
        .plan
        .steps
        .into_iter()
        .enumerate()
        .map(|(position, step)| {
            if step.position != position || expected_operation_ports(&step.operation_id).is_none() {
                return Err(BackendCommandError::unavailable());
            }
            validate_local_id(&step.node_id).map_err(|_| BackendCommandError::unavailable())?;
            for dependency in &step.dependencies {
                validate_local_id(dependency).map_err(|_| BackendCommandError::unavailable())?;
            }
            if step.dependencies.windows(2).any(|pair| pair[0] >= pair[1]) {
                return Err(BackendCommandError::unavailable());
            }
            Ok(WorkflowPlanStep {
                position: step.position,
                node_id: step.node_id,
                operation_id: step.operation_id,
                dependencies: step.dependencies,
            })
        })
        .collect::<Result<Vec<_>, _>>()?;
    let failures = wire
        .plan
        .failures
        .into_iter()
        .map(|failure| {
            if !matches!(
                failure.code.as_str(),
                "workflow-incompatible"
                    | "graph-invalid"
                    | "handler-missing"
                    | "handler-sdk-mismatch"
                    | "handler-input-mismatch"
                    | "handler-output-mismatch"
            ) {
                return Err(BackendCommandError::unavailable());
            }
            validate_text(&failure.path, 500, false)?;
            validate_text(&failure.message, 1_000, false)?;
            if let Some(node_id) = &failure.node_id {
                validate_local_id(node_id)?;
            }
            if let Some(operation_id) = &failure.operation_id
                && expected_operation_ports(operation_id).is_none()
            {
                return Err(BackendCommandError::unavailable());
            }
            Ok(WorkflowPlanFailure {
                code: failure.code,
                path: failure.path,
                message: failure.message,
                node_id: failure.node_id,
                operation_id: failure.operation_id,
            })
        })
        .collect::<Result<Vec<_>, _>>()?;
    Ok(WorkflowPlanResult {
        plan: WorkflowPlan {
            valid: wire.plan.valid,
            summary: wire.plan.summary,
            workflow_id: wire.plan.workflow_id,
            version: wire.plan.version,
            steps,
            failures,
        },
    })
}

fn validate_execution(
    wire: WireExecutionResult,
    workflow_id: &str,
    run_id: &str,
) -> Result<WorkflowExecutionResult, BackendCommandError> {
    let value = wire.execution;
    if value.run_id != run_id
        || value.workflow_id != workflow_id
        || value.steps.len() > MAX_WORKFLOW_NODES
        || value.completed_step_count != value.steps.len()
        || value.succeeded != value.failure.is_none()
        || (value.succeeded && value.outputs.is_empty())
        || (!value.succeeded && !value.outputs.is_empty())
    {
        return Err(BackendCommandError::unavailable());
    }
    validate_uuid(&value.run_id).map_err(|_| BackendCommandError::unavailable())?;
    validate_version(&value.version).map_err(|_| BackendCommandError::unavailable())?;
    let outputs = value
        .outputs
        .into_iter()
        .map(validate_runtime_output)
        .collect::<Result<Vec<_>, _>>()?;
    let steps = value
        .steps
        .into_iter()
        .enumerate()
        .map(|(position, step)| {
            if step.position != position || expected_operation_ports(&step.operation_id).is_none() {
                return Err(BackendCommandError::unavailable());
            }
            validate_local_id(&step.node_id).map_err(|_| BackendCommandError::unavailable())?;
            Ok(WorkflowExecutionStep {
                position: step.position,
                node_id: step.node_id,
                operation_id: step.operation_id,
                outputs: step
                    .outputs
                    .into_iter()
                    .map(validate_runtime_output)
                    .collect::<Result<Vec<_>, _>>()?,
            })
        })
        .collect::<Result<Vec<_>, _>>()?;
    let failure = value
        .failure
        .map(|failure| {
            if !matches!(
                failure.code.as_str(),
                "input-invalid"
                    | "handler-drift"
                    | "handler-error"
                    | "output-invalid"
                    | "event-delivery-failed"
            ) {
                return Err(BackendCommandError::unavailable());
            }
            validate_text(&failure.message, 1_000, false)?;
            if let Some(node_id) = &failure.node_id {
                validate_local_id(node_id)?;
            }
            if let Some(operation_id) = &failure.operation_id
                && expected_operation_ports(operation_id).is_none()
            {
                return Err(BackendCommandError::unavailable());
            }
            Ok(WorkflowExecutionFailure {
                code: failure.code,
                message: failure.message,
                node_id: failure.node_id,
                operation_id: failure.operation_id,
            })
        })
        .transpose()?;
    Ok(WorkflowExecutionResult {
        execution: WorkflowExecution {
            run_id: value.run_id,
            workflow_id: value.workflow_id,
            version: value.version,
            succeeded: value.succeeded,
            completed_step_count: value.completed_step_count,
            outputs,
            steps,
            failure,
        },
    })
}

fn validate_runtime_inputs(values: &[WorkflowRuntimeInput]) -> Result<(), BackendCommandError> {
    if values.len() > MAX_WORKFLOW_PORTS {
        return Err(BackendCommandError::invalid_request(
            "Workflow inputs are invalid.",
        ));
    }
    let mut ports = BTreeSet::new();
    for item in values {
        validate_local_id(&item.port_id)?;
        if !ports.insert(item.port_id.clone()) {
            return Err(BackendCommandError::invalid_request(
                "Workflow input ports must be unique.",
            ));
        }
        validate_runtime_value(&item.value)?;
    }
    Ok(())
}

fn validate_runtime_output(
    item: WireRuntimeValue,
) -> Result<WorkflowRuntimeValueView, BackendCommandError> {
    validate_local_id(&item.port_id).map_err(|_| BackendCommandError::unavailable())?;
    validate_runtime_value(&item.value).map_err(|_| BackendCommandError::unavailable())?;
    Ok(WorkflowRuntimeValueView {
        port_id: item.port_id,
        value: item.value,
    })
}

fn validate_runtime_value(value: &Value) -> Result<(), BackendCommandError> {
    let mut budget = 4_096usize;
    validate_runtime_node(value, 0, &mut budget)?;
    let encoded = serde_json::to_vec(value)
        .map_err(|_| BackendCommandError::invalid_request("Workflow runtime value is invalid."))?;
    if encoded.len() > MAX_WORKFLOW_RUNTIME_VALUE_BYTES {
        return Err(BackendCommandError::invalid_request(
            "Workflow runtime value is too large.",
        ));
    }
    Ok(())
}

fn validate_runtime_node(
    value: &Value,
    depth: usize,
    budget: &mut usize,
) -> Result<(), BackendCommandError> {
    *budget = budget.checked_sub(1).ok_or_else(|| {
        BackendCommandError::invalid_request("Workflow runtime value is too large.")
    })?;
    match value {
        Value::Null => Err(BackendCommandError::invalid_request(
            "Workflow runtime null values are not supported.",
        )),
        Value::String(text) => {
            if text.chars().count() > MAX_WORKFLOW_RUNTIME_STRING_LENGTH {
                Err(BackendCommandError::invalid_request(
                    "Workflow runtime text is too large.",
                ))
            } else {
                Ok(())
            }
        }
        Value::Bool(_) | Value::Number(_) => Ok(()),
        Value::Array(items) => {
            if depth >= 8 || items.len() > 256 {
                return Err(BackendCommandError::invalid_request(
                    "Workflow runtime collection is invalid.",
                ));
            }
            for item in items {
                validate_runtime_node(item, depth + 1, budget)?;
            }
            Ok(())
        }
        Value::Object(items) => {
            if depth >= 8 || items.len() > 256 {
                return Err(BackendCommandError::invalid_request(
                    "Workflow runtime collection is invalid.",
                ));
            }
            for (key, item) in items {
                if key.is_empty() || key.trim() != key || key.chars().count() > 128 {
                    return Err(BackendCommandError::invalid_request(
                        "Workflow runtime object key is invalid.",
                    ));
                }
                validate_runtime_node(item, depth + 1, budget)?;
            }
            Ok(())
        }
    }
}

fn validate_definition_ports(ports: &[WireDefinitionPort]) -> Result<(), BackendCommandError> {
    if ports.len() > MAX_WORKFLOW_PORTS {
        return Err(BackendCommandError::invalid_request(
            "Workflow ports are invalid.",
        ));
    }
    let mut identifiers = BTreeSet::new();
    for port in ports {
        validate_local_id(&port.id)?;
        validate_value_type(&port.value_type)?;
        validate_text(&port.description, 500, false)?;
        if !identifiers.insert(port.id.clone()) {
            return Err(BackendCommandError::invalid_request(
                "Workflow port identities must be unique.",
            ));
        }
    }
    Ok(())
}

fn validate_wire_endpoint(
    endpoint: &WireEndpoint,
    source: bool,
    workflow: &WireWorkflowBody,
) -> Result<(), BackendCommandError> {
    match endpoint {
        WireEndpoint::WorkflowInput(value) if source => {
            if workflow
                .inputs
                .iter()
                .any(|port| port.id == value.workflow_input)
            {
                Ok(())
            } else {
                Err(BackendCommandError::invalid_request(
                    "Workflow edge source is invalid.",
                ))
            }
        }
        WireEndpoint::WorkflowOutput(value) if !source => {
            if workflow
                .outputs
                .iter()
                .any(|port| port.id == value.workflow_output)
            {
                Ok(())
            } else {
                Err(BackendCommandError::invalid_request(
                    "Workflow edge target is invalid.",
                ))
            }
        }
        WireEndpoint::Node(value) => {
            validate_local_id(&value.node)?;
            validate_local_id(&value.port)?;
            let node = workflow
                .nodes
                .iter()
                .find(|node| node.id == value.node)
                .ok_or_else(|| {
                    BackendCommandError::invalid_request("Workflow edge node is invalid.")
                })?;
            let ports = if source { &node.outputs } else { &node.inputs };
            if ports.iter().any(|port| port.id == value.port) {
                Ok(())
            } else {
                Err(BackendCommandError::invalid_request(
                    "Workflow edge port is invalid.",
                ))
            }
        }
        _ => Err(BackendCommandError::invalid_request(
            "Workflow edge direction is invalid.",
        )),
    }
}

fn validate_value_type(value: &str) -> Result<(), BackendCommandError> {
    if matches!(
        value,
        "string" | "integer" | "number" | "boolean" | "object" | "array"
    ) {
        Ok(())
    } else {
        Err(BackendCommandError::invalid_request(
            "Workflow value type is invalid.",
        ))
    }
}

fn validate_local_id(value: &str) -> Result<(), BackendCommandError> {
    if valid_segmented_id(value, false) {
        Ok(())
    } else {
        Err(BackendCommandError::invalid_request(
            "Workflow local identifier is invalid.",
        ))
    }
}

fn validate_vendor_id(value: &str) -> Result<(), BackendCommandError> {
    if value.len() <= 128
        && value.split('.').count() >= 2
        && value
            .split('.')
            .all(|segment| valid_segmented_id(segment, false))
    {
        Ok(())
    } else {
        Err(BackendCommandError::invalid_request(
            "Workflow identity is invalid.",
        ))
    }
}

fn valid_segmented_id(value: &str, allow_dot: bool) -> bool {
    !value.is_empty()
        && value.len() <= 64
        && !value.starts_with('-')
        && !value.ends_with('-')
        && value.bytes().all(|byte| {
            byte.is_ascii_lowercase()
                || byte.is_ascii_digit()
                || byte == b'-'
                || (allow_dot && byte == b'.')
        })
        && !value.contains("--")
}

fn validate_version(value: &str) -> Result<(), BackendCommandError> {
    let parts = value.split('.').collect::<Vec<_>>();
    if parts.len() == 3
        && parts.iter().all(|part| {
            !part.is_empty()
                && part.bytes().all(|byte| byte.is_ascii_digit())
                && (part == &"0" || !part.starts_with('0'))
        })
    {
        Ok(())
    } else {
        Err(BackendCommandError::invalid_request(
            "Workflow version is invalid.",
        ))
    }
}

fn validate_uuid(value: &str) -> Result<(), BackendCommandError> {
    let bytes = value.as_bytes();
    let valid = bytes.len() == 36
        && bytes.iter().enumerate().all(|(index, byte)| {
            if matches!(index, 8 | 13 | 18 | 23) {
                *byte == b'-'
            } else {
                byte.is_ascii_digit() || matches!(byte, b'a'..=b'f')
            }
        });
    if valid {
        Ok(())
    } else {
        Err(BackendCommandError::invalid_request(
            "Workflow run identity is invalid.",
        ))
    }
}

fn validate_confirmation(value: bool) -> Result<(), BackendCommandError> {
    if value {
        Ok(())
    } else {
        Err(BackendCommandError::invalid_request(
            "Workflow operation requires confirmation.",
        ))
    }
}

fn validate_text(
    value: &str,
    maximum: usize,
    allow_empty: bool,
) -> Result<(), BackendCommandError> {
    let trimmed = value.trim();
    if trimmed.chars().count() > maximum || (!allow_empty && trimmed.is_empty()) {
        Err(BackendCommandError::invalid_request(
            "Workflow text is invalid.",
        ))
    } else {
        Ok(())
    }
}

fn expected_operation_ports(
    operation_id: &str,
) -> Option<(Vec<WireOperationPort>, Vec<WireOperationPort>)> {
    let port = |port_id: &str, description: &str| WireOperationPort {
        port_id: port_id.to_owned(),
        value_type: "string".to_owned(),
        description: description.to_owned(),
    };
    match operation_id {
        "ups.echo-text" | "ups.uppercase-text" => Some((
            vec![port("value", "Text supplied to the operation.")],
            vec![port("value", "Text returned by the operation.")],
        )),
        PROMPT_OPERATION => Some((
            vec![
                port("project-id", "Owning durable project identifier."),
                port("prompt-id", "Durable project-owned prompt identifier."),
                port(
                    "provider-id",
                    "Existing host-authorized provider identifier selected for this run.",
                ),
            ],
            vec![port(
                "result",
                "Bounded text returned by the authorized provider.",
            )],
        )),
        _ => None,
    }
}

fn expected_definition_ports(
    operation_id: &str,
) -> Option<(Vec<WireDefinitionPort>, Vec<WireDefinitionPort>)> {
    expected_operation_ports(operation_id).map(|(inputs, outputs)| {
        (
            inputs.into_iter().map(operation_definition_port).collect(),
            outputs.into_iter().map(operation_definition_port).collect(),
        )
    })
}

fn operation_definition_port(value: WireOperationPort) -> WireDefinitionPort {
    WireDefinitionPort {
        id: value.port_id,
        value_type: value.value_type,
        description: value.description,
    }
}

fn operation_port_view(value: WireOperationPort) -> WorkflowOperationPort {
    WorkflowOperationPort {
        port_id: value.port_id,
        value_type: value.value_type,
        description: value.description,
    }
}

fn input_port_wire(value: &WorkflowPortInput) -> WireDefinitionPort {
    WireDefinitionPort {
        id: value.id.clone(),
        value_type: value.value_type.clone(),
        description: value.description.clone(),
    }
}

fn input_edge_wire(value: &WorkflowEdgeInput) -> WireEdge {
    WireEdge {
        source: input_endpoint_wire(&value.source),
        target: input_endpoint_wire(&value.target),
    }
}

fn input_endpoint_wire(value: &WorkflowEndpointInput) -> WireEndpoint {
    match value {
        WorkflowEndpointInput::WorkflowInput(endpoint) => {
            WireEndpoint::WorkflowInput(WireWorkflowInputEndpoint {
                workflow_input: endpoint.workflow_input.clone(),
            })
        }
        WorkflowEndpointInput::WorkflowOutput(endpoint) => {
            WireEndpoint::WorkflowOutput(WireWorkflowOutputEndpoint {
                workflow_output: endpoint.workflow_output.clone(),
            })
        }
        WorkflowEndpointInput::Node(endpoint) => WireEndpoint::Node(WireNodeEndpoint {
            node: endpoint.node.clone(),
            port: endpoint.port.clone(),
        }),
    }
}

fn definition_port_view(value: &WireDefinitionPort) -> WorkflowPortView {
    WorkflowPortView {
        id: value.id.clone(),
        value_type: value.value_type.clone(),
        description: value.description.clone(),
    }
}

fn endpoint_view(value: &WireEndpoint) -> WorkflowEndpointView {
    match value {
        WireEndpoint::WorkflowInput(endpoint) => WorkflowEndpointView {
            kind: "workflow-input".to_owned(),
            port_id: endpoint.workflow_input.clone(),
            node_id: None,
        },
        WireEndpoint::WorkflowOutput(endpoint) => WorkflowEndpointView {
            kind: "workflow-output".to_owned(),
            port_id: endpoint.workflow_output.clone(),
            node_id: None,
        },
        WireEndpoint::Node(endpoint) => WorkflowEndpointView {
            kind: "node".to_owned(),
            port_id: endpoint.port.clone(),
            node_id: Some(endpoint.node.clone()),
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn operation_catalog_and_runtime_values_are_closed_and_bounded() {
        assert!(expected_operation_ports("ups.echo-text").is_some());
        assert!(expected_operation_ports(PROMPT_OPERATION).is_some());
        assert!(expected_operation_ports("evil.dynamic").is_none());
        assert!(validate_runtime_value(&Value::String("safe".to_owned())).is_ok());
        assert!(validate_runtime_value(&Value::String("x".repeat(1_001))).is_err());
        assert!(validate_runtime_value(&Value::Null).is_err());
    }

    #[test]
    fn workflow_and_run_identifiers_are_independently_validated() {
        assert!(validate_vendor_id("ups.user-flow").is_ok());
        assert!(validate_vendor_id("dynamic_import").is_err());
        assert!(validate_local_id("provider-id").is_ok());
        assert!(validate_local_id("provider_id").is_err());
        assert!(validate_uuid("550e8400-e29b-41d4-a716-446655440000").is_ok());
        assert!(validate_uuid("../run").is_err());
    }
}
