//! Fixed, correlated lifecycle bridge to the bundled application sidecar.

use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};
use std::fmt;
use std::sync::mpsc::{self, Receiver};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri::{AppHandle, Manager};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};

const IPC_PROTOCOL_VERSION: u32 = 1;
const STORAGE_SCHEMA_VERSION: u32 = 1;
const MAX_IPC_MESSAGE_BYTES: usize = 16_384;
const MAX_LIBRARY_ITEMS: usize = 50;
const RESPONSE_TIMEOUT: Duration = Duration::from_secs(3);
const READINESS_COMMAND: &str = "application.readiness";
const PROJECT_LIST_COMMAND: &str = "library.projects.list";
const PROJECT_CREATE_COMMAND: &str = "library.projects.create";
const PROJECT_DELETE_COMMAND: &str = "library.projects.delete";
const PROMPT_LIST_COMMAND: &str = "library.prompts.list";
const PROMPT_CREATE_COMMAND: &str = "library.prompts.create";
const PROMPT_GET_COMMAND: &str = "library.prompts.get";
const PROMPT_UPDATE_COMMAND: &str = "library.prompts.update";
const PROMPT_DELETE_COMMAND: &str = "library.prompts.delete";
const PROMPT_SEARCH_COMMAND: &str = "library.prompts.search";
const PROMPT_COMPOSE_COMMAND: &str = "library.prompts.compose";
const PROMPT_EXECUTE_OFFLINE_COMMAND: &str = "library.prompts.execute-offline";
const OFFLINE_REFERENCE_PROVIDER: &str = "ups.offline-echo";
const OFFLINE_REFERENCE_VERSION: &str = "1.0.0";
const MAX_COMPOSED_PROMPT_LENGTH: usize = 12_500;
const MAX_EXECUTION_OUTPUT_LENGTH: usize = MAX_COMPOSED_PROMPT_LENGTH + 64;
const SIDECAR_IDENTITY: &str = "com.universalpromptstudio.backend";
const SIDECAR_NAME: &str = "universal-prompt-studio-backend";
const APP_DATA_ENV: &str = "UPS_APP_DATA_DIR";
const CAPABILITIES: [&str; 12] = [
    READINESS_COMMAND,
    PROJECT_LIST_COMMAND,
    PROJECT_CREATE_COMMAND,
    PROJECT_DELETE_COMMAND,
    PROMPT_LIST_COMMAND,
    PROMPT_CREATE_COMMAND,
    PROMPT_GET_COMMAND,
    PROMPT_UPDATE_COMMAND,
    PROMPT_DELETE_COMMAND,
    PROMPT_SEARCH_COMMAND,
    PROMPT_COMPOSE_COMMAND,
    PROMPT_EXECUTE_OFFLINE_COMMAND,
];

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BackendReadiness {
    status: String,
    application_version: String,
    protocol_version: u32,
    storage_schema_version: u32,
    capabilities: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct ProjectSummary {
    project_id: String,
    name: String,
    description: String,
    created_at: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct PromptBlockSummary {
    block_type: String,
    content: String,
    order: usize,
    enabled: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct PromptSummary {
    prompt_id: String,
    project_id: String,
    title: String,
    category: Option<String>,
    tags: Vec<String>,
    blocks: Vec<PromptBlockSummary>,
    created_at: String,
    updated_at: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectList {
    projects: Vec<ProjectSummary>,
    has_more: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PromptList {
    prompts: Vec<PromptSummary>,
    has_more: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CreatedProject {
    project: ProjectSummary,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CreatedPrompt {
    prompt: PromptSummary,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DeletedProject {
    deleted_project_id: String,
    deleted_prompt_count: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DeletedPrompt {
    deleted_prompt_id: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PromptCompositionSummary {
    project_id: String,
    prompt_id: String,
    title: String,
    final_prompt: String,
    enabled_block_count: usize,
    total_block_count: usize,
    character_count: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct OfflineExecutionSummary {
    project_id: String,
    prompt_id: String,
    provider_id: String,
    provider_version: String,
    execution_id: String,
    output: String,
    input_units: usize,
    output_units: usize,
    prompt_character_count: usize,
}
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(
    deny_unknown_fields,
    rename_all(serialize = "snake_case", deserialize = "camelCase")
)]
pub struct PromptBlockInput {
    block_type: String,
    content: String,
    enabled: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct BackendCommandError {
    code: String,
    message: String,
    #[serde(skip)]
    restart_process: bool,
}

impl BackendCommandError {
    fn new(code: &str, message: &str, restart_process: bool) -> Self {
        Self {
            code: code.to_owned(),
            message: message.to_owned(),
            restart_process,
        }
    }

    fn invalid_request(message: &str) -> Self {
        Self::new("library.invalid_input", message, false)
    }

    fn unavailable() -> Self {
        Self::new(
            "backend.unavailable",
            "The local application backend is unavailable.",
            true,
        )
    }
}

impl fmt::Display for BackendCommandError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}", self.message)
    }
}

#[derive(Debug, Serialize)]
struct WireRequest<'a, P: Serialize> {
    schema_version: u32,
    request_id: &'a str,
    command: &'static str,
    payload: P,
}

#[derive(Debug, Default, Serialize)]
struct EmptyPayload {}

#[derive(Debug, Serialize)]
struct CreateProjectPayload<'a> {
    name: &'a str,
    description: &'a str,
}

#[derive(Debug, Serialize)]
struct ProjectPayload<'a> {
    project_id: &'a str,
}

#[derive(Debug, Serialize)]
struct DeleteProjectPayload<'a> {
    project_id: &'a str,
    confirm: bool,
}

#[derive(Debug, Serialize)]
struct CreatePromptPayload<'a> {
    project_id: &'a str,
    title: &'a str,
}

#[derive(Debug, Serialize)]
struct PromptPayload<'a> {
    project_id: &'a str,
    prompt_id: &'a str,
}

#[derive(Debug, Serialize)]
struct DeletePromptPayload<'a> {
    project_id: &'a str,
    prompt_id: &'a str,
    confirm: bool,
}

#[derive(Debug, Serialize)]
struct SearchPromptPayload<'a> {
    project_id: &'a str,
    query: &'a str,
}

#[derive(Debug, Serialize)]
struct ExecutePromptPayload<'a> {
    project_id: &'a str,
    prompt_id: &'a str,
    provider_id: &'static str,
    confirm: bool,
}

#[derive(Debug, Serialize)]
struct UpdatePromptPayload<'a> {
    project_id: &'a str,
    prompt_id: &'a str,
    title: &'a str,
    category: &'a Option<String>,
    tags: &'a [String],
    blocks: &'a [PromptBlockInput],
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireResponse<T> {
    schema_version: u32,
    request_id: String,
    ok: bool,
    result: Option<T>,
    error: Option<WireError>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireReadiness {
    status: String,
    sidecar_identity: String,
    application_version: String,
    protocol_version: u32,
    storage_schema_version: u32,
    capabilities: Vec<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireProjectList {
    projects: Vec<WireProject>,
    has_more: bool,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WirePromptList {
    prompts: Vec<WirePrompt>,
    has_more: bool,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireCreatedProject {
    project: WireProject,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireCreatedPrompt {
    prompt: WirePrompt,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireDeletedProject {
    deleted_project_id: String,
    deleted_prompt_count: usize,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireDeletedPrompt {
    deleted_prompt_id: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireProject {
    project_id: String,
    name: String,
    description: String,
    created_at: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireCompositionResult {
    composition: WireComposition,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireComposition {
    project_id: String,
    prompt_id: String,
    title: String,
    final_prompt: String,
    enabled_block_count: usize,
    total_block_count: usize,
    character_count: usize,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireExecutionResult {
    execution: WireExecution,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireExecution {
    project_id: String,
    prompt_id: String,
    provider_id: String,
    provider_version: String,
    execution_id: String,
    output: String,
    input_units: usize,
    output_units: usize,
    prompt_character_count: usize,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WirePrompt {
    prompt_id: String,
    project_id: String,
    title: String,
    category: Option<String>,
    tags: Vec<String>,
    blocks: Vec<WirePromptBlock>,
    created_at: String,
    updated_at: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WirePromptBlock {
    block_type: String,
    content: String,
    order: usize,
    enabled: bool,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireError {
    code: String,
    message: String,
}

struct BackendProcess {
    child: Option<CommandChild>,
    output: Receiver<Result<Vec<u8>, ()>>,
}

impl BackendProcess {
    fn spawn(app: &AppHandle) -> Result<Self, BackendCommandError> {
        let app_data = app
            .path()
            .app_data_dir()
            .map_err(|_| BackendCommandError::unavailable())?;
        std::fs::create_dir_all(&app_data).map_err(|_| BackendCommandError::unavailable())?;
        let mut command = app
            .shell()
            .sidecar(SIDECAR_NAME)
            .map_err(|_| BackendCommandError::unavailable())?
            .env_clear()
            .env(APP_DATA_ENV, app_data);
        for key in ["SystemRoot", "TEMP", "TMP"] {
            if let Some(value) = std::env::var_os(key) {
                command = command.env(key, value);
            }
        }
        let (mut events, child) = command
            .spawn()
            .map_err(|_| BackendCommandError::unavailable())?;
        let (sender, output) = mpsc::channel();
        tauri::async_runtime::spawn(async move {
            while let Some(event) = events.recv().await {
                match event {
                    CommandEvent::Stdout(value) if value.len() <= MAX_IPC_MESSAGE_BYTES => {
                        if sender.send(Ok(value)).is_err() {
                            break;
                        }
                    }
                    CommandEvent::Stdout(_)
                    | CommandEvent::Error(_)
                    | CommandEvent::Terminated(_) => {
                        let _ = sender.send(Err(()));
                        break;
                    }
                    CommandEvent::Stderr(_) => {}
                    _ => {}
                }
            }
        });
        Ok(Self {
            child: Some(child),
            output,
        })
    }

    fn request<P, T>(
        &mut self,
        request_id: &str,
        command: &'static str,
        payload: P,
    ) -> Result<T, BackendCommandError>
    where
        P: Serialize,
        T: DeserializeOwned,
    {
        let request = WireRequest {
            schema_version: IPC_PROTOCOL_VERSION,
            request_id,
            command,
            payload,
        };
        let mut encoded =
            serde_json::to_vec(&request).map_err(|_| BackendCommandError::unavailable())?;
        if encoded.len() > MAX_IPC_MESSAGE_BYTES {
            return Err(BackendCommandError::invalid_request(
                "The library request is too large.",
            ));
        }
        encoded.push(b'\n');
        self.child
            .as_mut()
            .ok_or_else(BackendCommandError::unavailable)?
            .write(&encoded)
            .map_err(|_| BackendCommandError::unavailable())?;
        let line = self
            .output
            .recv_timeout(RESPONSE_TIMEOUT)
            .map_err(|_| BackendCommandError::unavailable())?
            .map_err(|_| BackendCommandError::unavailable())?;
        decode_response(&line, request_id)
    }
}

impl Drop for BackendProcess {
    fn drop(&mut self) {
        if let Some(child) = self.child.take() {
            let _ = child.kill();
        }
    }
}

#[derive(Clone)]
pub struct BackendManager {
    app: AppHandle,
    process: Arc<Mutex<Option<BackendProcess>>>,
}

impl BackendManager {
    pub fn new(app: AppHandle) -> Self {
        Self {
            app,
            process: Arc::new(Mutex::new(None)),
        }
    }

    fn request<P, T>(
        &self,
        request_id: &str,
        command: &'static str,
        payload: P,
    ) -> Result<T, BackendCommandError>
    where
        P: Serialize,
        T: DeserializeOwned,
    {
        if !valid_request_id(request_id) {
            return Err(BackendCommandError::invalid_request(
                "The library request identifier is invalid.",
            ));
        }
        let mut process = self
            .process
            .lock()
            .map_err(|_| BackendCommandError::unavailable())?;
        if process.is_none() {
            *process = Some(BackendProcess::spawn(&self.app)?);
        }
        let result = process
            .as_mut()
            .ok_or_else(BackendCommandError::unavailable)?
            .request(request_id, command, payload);
        if result
            .as_ref()
            .err()
            .is_some_and(|error| error.restart_process)
        {
            *process = None;
        }
        result
    }
}

#[tauri::command]
pub async fn backend_readiness(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
) -> Result<BackendReadiness, BackendCommandError> {
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireReadiness =
            manager.request(&request_id, READINESS_COMMAND, EmptyPayload {})?;
        validate_readiness(wire)
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn library_delete_project(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    project_id: String,
    confirm: bool,
) -> Result<DeletedProject, BackendCommandError> {
    validate_identifier(&project_id)?;
    validate_confirmation(confirm)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireDeletedProject = manager.request(
            &request_id,
            PROJECT_DELETE_COMMAND,
            DeleteProjectPayload {
                project_id: &project_id,
                confirm,
            },
        )?;
        if wire.deleted_project_id != project_id {
            return Err(BackendCommandError::unavailable());
        }
        Ok(DeletedProject {
            deleted_project_id: wire.deleted_project_id,
            deleted_prompt_count: wire.deleted_prompt_count,
        })
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn library_projects(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
) -> Result<ProjectList, BackendCommandError> {
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireProjectList =
            manager.request(&request_id, PROJECT_LIST_COMMAND, EmptyPayload {})?;
        validate_project_list(wire)
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn library_create_project(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    name: String,
    description: String,
) -> Result<CreatedProject, BackendCommandError> {
    validate_text(&name, 120, false)?;
    validate_text(&description, 1_000, true)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireCreatedProject = manager.request(
            &request_id,
            PROJECT_CREATE_COMMAND,
            CreateProjectPayload {
                name: &name,
                description: &description,
            },
        )?;
        Ok(CreatedProject {
            project: validate_project(wire.project)?,
        })
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn library_prompts(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    project_id: String,
) -> Result<PromptList, BackendCommandError> {
    validate_identifier(&project_id)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WirePromptList = manager.request(
            &request_id,
            PROMPT_LIST_COMMAND,
            ProjectPayload {
                project_id: &project_id,
            },
        )?;
        validate_prompt_list(wire, &project_id)
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn library_create_prompt(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    project_id: String,
    title: String,
) -> Result<CreatedPrompt, BackendCommandError> {
    validate_identifier(&project_id)?;
    validate_text(&title, 120, false)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireCreatedPrompt = manager.request(
            &request_id,
            PROMPT_CREATE_COMMAND,
            CreatePromptPayload {
                project_id: &project_id,
                title: &title,
            },
        )?;
        let prompt = validate_prompt(wire.prompt)?;
        if prompt.project_id != project_id {
            return Err(BackendCommandError::unavailable());
        }
        Ok(CreatedPrompt { prompt })
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn library_get_prompt(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    project_id: String,
    prompt_id: String,
) -> Result<CreatedPrompt, BackendCommandError> {
    validate_identifier(&project_id)?;
    validate_identifier(&prompt_id)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireCreatedPrompt = manager.request(
            &request_id,
            PROMPT_GET_COMMAND,
            PromptPayload {
                project_id: &project_id,
                prompt_id: &prompt_id,
            },
        )?;
        Ok(CreatedPrompt {
            prompt: validate_owned_prompt(wire.prompt, &project_id, Some(&prompt_id))?,
        })
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
#[allow(clippy::too_many_arguments)]
pub async fn library_update_prompt(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    project_id: String,
    prompt_id: String,
    title: String,
    category: Option<String>,
    tags: Vec<String>,
    blocks: Vec<PromptBlockInput>,
) -> Result<CreatedPrompt, BackendCommandError> {
    validate_identifier(&project_id)?;
    validate_identifier(&prompt_id)?;
    validate_text(&title, 120, false)?;
    if let Some(value) = &category {
        validate_text(value, 80, true)?;
    }
    validate_tags(&tags)?;
    validate_block_inputs(&blocks)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireCreatedPrompt = manager.request(
            &request_id,
            PROMPT_UPDATE_COMMAND,
            UpdatePromptPayload {
                project_id: &project_id,
                prompt_id: &prompt_id,
                title: &title,
                category: &category,
                tags: &tags,
                blocks: &blocks,
            },
        )?;
        Ok(CreatedPrompt {
            prompt: validate_owned_prompt(wire.prompt, &project_id, Some(&prompt_id))?,
        })
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn library_delete_prompt(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    project_id: String,
    prompt_id: String,
    confirm: bool,
) -> Result<DeletedPrompt, BackendCommandError> {
    validate_identifier(&project_id)?;
    validate_identifier(&prompt_id)?;
    validate_confirmation(confirm)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireDeletedPrompt = manager.request(
            &request_id,
            PROMPT_DELETE_COMMAND,
            DeletePromptPayload {
                project_id: &project_id,
                prompt_id: &prompt_id,
                confirm,
            },
        )?;
        if wire.deleted_prompt_id != prompt_id {
            return Err(BackendCommandError::unavailable());
        }
        Ok(DeletedPrompt {
            deleted_prompt_id: wire.deleted_prompt_id,
        })
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn library_search_prompts(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    project_id: String,
    query: String,
) -> Result<PromptList, BackendCommandError> {
    validate_identifier(&project_id)?;
    validate_text(&query, 120, false)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WirePromptList = manager.request(
            &request_id,
            PROMPT_SEARCH_COMMAND,
            SearchPromptPayload {
                project_id: &project_id,
                query: &query,
            },
        )?;
        validate_prompt_list(wire, &project_id)
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn library_compose_prompt(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    project_id: String,
    prompt_id: String,
) -> Result<PromptCompositionSummary, BackendCommandError> {
    validate_identifier(&project_id)?;
    validate_identifier(&prompt_id)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireCompositionResult = manager.request(
            &request_id,
            PROMPT_COMPOSE_COMMAND,
            PromptPayload {
                project_id: &project_id,
                prompt_id: &prompt_id,
            },
        )?;
        validate_composition(wire.composition, &project_id, &prompt_id)
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn library_execute_prompt_offline(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    project_id: String,
    prompt_id: String,
    provider_id: String,
    confirm: bool,
) -> Result<OfflineExecutionSummary, BackendCommandError> {
    validate_identifier(&project_id)?;
    validate_identifier(&prompt_id)?;
    if provider_id != OFFLINE_REFERENCE_PROVIDER {
        return Err(BackendCommandError::invalid_request(
            "Only the offline reference provider is supported.",
        ));
    }
    validate_confirmation(confirm)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let wire: WireExecutionResult = manager.request(
            &request_id,
            PROMPT_EXECUTE_OFFLINE_COMMAND,
            ExecutePromptPayload {
                project_id: &project_id,
                prompt_id: &prompt_id,
                provider_id: OFFLINE_REFERENCE_PROVIDER,
                confirm,
            },
        )?;
        validate_execution(wire.execution, &project_id, &prompt_id)
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

fn decode_response<T: DeserializeOwned>(
    line: &[u8],
    expected_request_id: &str,
) -> Result<T, BackendCommandError> {
    let response: WireResponse<T> =
        serde_json::from_slice(line).map_err(|_| BackendCommandError::unavailable())?;
    if response.schema_version != IPC_PROTOCOL_VERSION || response.request_id != expected_request_id
    {
        return Err(BackendCommandError::unavailable());
    }
    if response.ok {
        if response.error.is_some() {
            return Err(BackendCommandError::unavailable());
        }
        return response.result.ok_or_else(BackendCommandError::unavailable);
    }
    if response.result.is_some() {
        return Err(BackendCommandError::unavailable());
    }
    let error = response
        .error
        .ok_or_else(BackendCommandError::unavailable)?;
    map_wire_error(error)
}

fn map_wire_error<T>(error: WireError) -> Result<T, BackendCommandError> {
    if error.code.is_empty()
        || error.code.len() > 64
        || error.message.is_empty()
        || error.message.len() > 256
    {
        return Err(BackendCommandError::unavailable());
    }
    let safe = match error.code.as_str() {
        "ipc.invalid_payload" => {
            BackendCommandError::invalid_request("The project or prompt information is invalid.")
        }
        "library.not_found" => BackendCommandError::new(
            "library.not_found",
            "The selected library item no longer exists.",
            false,
        ),
        "storage.invalid_database" => BackendCommandError::new(
            "storage.invalid_database",
            "The prompt library is invalid and was left unchanged.",
            true,
        ),
        "storage.future_schema" => BackendCommandError::new(
            "storage.future_schema",
            "The prompt library was created by a newer application version.",
            true,
        ),
        "storage.unavailable" => BackendCommandError::new(
            "storage.unavailable",
            "The prompt library is unavailable.",
            true,
        ),
        "execution.failed" => BackendCommandError::new(
            "execution.failed",
            "Offline prompt execution failed safely.",
            false,
        ),
        _ => BackendCommandError::unavailable(),
    };
    Err(safe)
}

fn validate_readiness(value: WireReadiness) -> Result<BackendReadiness, BackendCommandError> {
    if value.status != "ready"
        || value.sidecar_identity != SIDECAR_IDENTITY
        || value.application_version != env!("CARGO_PKG_VERSION")
        || value.protocol_version != IPC_PROTOCOL_VERSION
        || value.storage_schema_version != STORAGE_SCHEMA_VERSION
        || value.capabilities != CAPABILITIES
    {
        return Err(BackendCommandError::unavailable());
    }
    Ok(BackendReadiness {
        status: value.status,
        application_version: value.application_version,
        protocol_version: value.protocol_version,
        storage_schema_version: value.storage_schema_version,
        capabilities: value.capabilities,
    })
}

fn validate_composition(
    value: WireComposition,
    project_id: &str,
    prompt_id: &str,
) -> Result<PromptCompositionSummary, BackendCommandError> {
    let character_count = value.final_prompt.chars().count();
    if value.project_id != project_id
        || value.prompt_id != prompt_id
        || value.final_prompt.trim().is_empty()
        || character_count > MAX_COMPOSED_PROMPT_LENGTH
        || value.character_count != character_count
        || value.enabled_block_count == 0
        || value.total_block_count < value.enabled_block_count
        || value.total_block_count > 12
    {
        return Err(BackendCommandError::unavailable());
    }
    validate_text(&value.title, 120, false)?;
    Ok(PromptCompositionSummary {
        project_id: value.project_id,
        prompt_id: value.prompt_id,
        title: value.title,
        final_prompt: value.final_prompt,
        enabled_block_count: value.enabled_block_count,
        total_block_count: value.total_block_count,
        character_count: value.character_count,
    })
}

fn validate_execution(
    value: WireExecution,
    project_id: &str,
    prompt_id: &str,
) -> Result<OfflineExecutionSummary, BackendCommandError> {
    let output_count = value.output.chars().count();
    if value.project_id != project_id
        || value.prompt_id != prompt_id
        || value.provider_id != OFFLINE_REFERENCE_PROVIDER
        || value.provider_version != OFFLINE_REFERENCE_VERSION
        || value.output.trim().is_empty()
        || output_count > MAX_EXECUTION_OUTPUT_LENGTH
        || value.prompt_character_count == 0
        || value.prompt_character_count > MAX_COMPOSED_PROMPT_LENGTH
    {
        return Err(BackendCommandError::unavailable());
    }
    validate_identifier(&value.execution_id)?;
    Ok(OfflineExecutionSummary {
        project_id: value.project_id,
        prompt_id: value.prompt_id,
        provider_id: value.provider_id,
        provider_version: value.provider_version,
        execution_id: value.execution_id,
        output: value.output,
        input_units: value.input_units,
        output_units: value.output_units,
        prompt_character_count: value.prompt_character_count,
    })
}

fn validate_project_list(value: WireProjectList) -> Result<ProjectList, BackendCommandError> {
    if value.projects.len() > MAX_LIBRARY_ITEMS {
        return Err(BackendCommandError::unavailable());
    }
    let projects = value
        .projects
        .into_iter()
        .map(validate_project)
        .collect::<Result<Vec<_>, _>>()?;
    Ok(ProjectList {
        projects,
        has_more: value.has_more,
    })
}

fn validate_prompt_list(
    value: WirePromptList,
    project_id: &str,
) -> Result<PromptList, BackendCommandError> {
    if value.prompts.len() > MAX_LIBRARY_ITEMS {
        return Err(BackendCommandError::unavailable());
    }
    let prompts = value
        .prompts
        .into_iter()
        .map(validate_prompt)
        .collect::<Result<Vec<_>, _>>()?;
    if prompts.iter().any(|prompt| prompt.project_id != project_id) {
        return Err(BackendCommandError::unavailable());
    }
    Ok(PromptList {
        prompts,
        has_more: value.has_more,
    })
}

fn validate_project(value: WireProject) -> Result<ProjectSummary, BackendCommandError> {
    validate_identifier(&value.project_id)?;
    validate_text(&value.name, 120, false)?;
    validate_text(&value.description, 1_000, true)?;
    validate_timestamp(&value.created_at)?;
    Ok(ProjectSummary {
        project_id: value.project_id,
        name: value.name,
        description: value.description,
        created_at: value.created_at,
    })
}

fn validate_prompt(value: WirePrompt) -> Result<PromptSummary, BackendCommandError> {
    validate_identifier(&value.prompt_id)?;
    validate_identifier(&value.project_id)?;
    validate_text(&value.title, 120, false)?;
    if let Some(category) = &value.category {
        validate_text(category, 80, false)?;
    }
    validate_tags(&value.tags)?;
    if value.blocks.len() > 12 {
        return Err(BackendCommandError::unavailable());
    }
    let mut total_content = 0usize;
    let blocks = value
        .blocks
        .into_iter()
        .enumerate()
        .map(|(order, block)| {
            if block.order != order || !valid_block_type(&block.block_type) {
                return Err(BackendCommandError::unavailable());
            }
            validate_text(&block.content, 2_000, false)?;
            total_content += block.content.trim().len();
            if total_content > 12_000 {
                return Err(BackendCommandError::unavailable());
            }
            Ok(PromptBlockSummary {
                block_type: block.block_type,
                content: block.content,
                order: block.order,
                enabled: block.enabled,
            })
        })
        .collect::<Result<Vec<_>, _>>()?;
    validate_timestamp(&value.created_at)?;
    validate_timestamp(&value.updated_at)?;
    Ok(PromptSummary {
        prompt_id: value.prompt_id,
        project_id: value.project_id,
        title: value.title,
        category: value.category,
        tags: value.tags,
        blocks,
        created_at: value.created_at,
        updated_at: value.updated_at,
    })
}

fn validate_owned_prompt(
    value: WirePrompt,
    project_id: &str,
    prompt_id: Option<&str>,
) -> Result<PromptSummary, BackendCommandError> {
    let prompt = validate_prompt(value)?;
    if prompt.project_id != project_id
        || prompt_id.is_some_and(|expected| prompt.prompt_id != expected)
    {
        return Err(BackendCommandError::unavailable());
    }
    Ok(prompt)
}

fn validate_confirmation(value: bool) -> Result<(), BackendCommandError> {
    if value {
        Ok(())
    } else {
        Err(BackendCommandError::invalid_request(
            "Operation requires confirmation.",
        ))
    }
}

fn validate_tags(values: &[String]) -> Result<(), BackendCommandError> {
    if values.len() > 10 {
        return Err(BackendCommandError::invalid_request(
            "Prompt tags are invalid.",
        ));
    }
    let mut normalized = Vec::with_capacity(values.len());
    for value in values {
        validate_text(value, 32, false)?;
        if value.contains(['\n', '\r']) {
            return Err(BackendCommandError::invalid_request(
                "Prompt tags are invalid.",
            ));
        }
        let folded = value.to_lowercase();
        if normalized.contains(&folded) {
            return Err(BackendCommandError::invalid_request(
                "Prompt tags are invalid.",
            ));
        }
        normalized.push(folded);
    }
    Ok(())
}

fn validate_block_inputs(values: &[PromptBlockInput]) -> Result<(), BackendCommandError> {
    if values.len() > 12 {
        return Err(BackendCommandError::invalid_request(
            "Prompt blocks are invalid.",
        ));
    }
    let mut total_content = 0usize;
    for value in values {
        if !valid_block_type(&value.block_type) {
            return Err(BackendCommandError::invalid_request(
                "Prompt blocks are invalid.",
            ));
        }
        validate_text(&value.content, 2_000, false)?;
        total_content += value.content.trim().len();
        if total_content > 12_000 {
            return Err(BackendCommandError::invalid_request(
                "Prompt blocks are invalid.",
            ));
        }
    }
    Ok(())
}

fn valid_block_type(value: &str) -> bool {
    matches!(
        value,
        "role"
            | "goal"
            | "context"
            | "audience"
            | "constraints"
            | "requirements"
            | "tone"
            | "output_format"
            | "reasoning_style"
            | "examples"
            | "validation_rules"
            | "final_instructions"
    )
}

fn valid_request_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 64
        && value.bytes().enumerate().all(|(index, byte)| {
            byte.is_ascii_alphanumeric() || (index > 0 && matches!(byte, b'.' | b'_' | b':' | b'-'))
        })
}

fn validate_identifier(value: &str) -> Result<(), BackendCommandError> {
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
            "The project identifier is invalid.",
        ))
    }
}

fn validate_text(
    value: &str,
    maximum: usize,
    allow_empty: bool,
) -> Result<(), BackendCommandError> {
    let trimmed = value.trim();
    if trimmed.len() > maximum || (!allow_empty && trimmed.is_empty()) {
        return Err(BackendCommandError::invalid_request(
            "The project or prompt information is invalid.",
        ));
    }
    Ok(())
}

fn validate_timestamp(value: &str) -> Result<(), BackendCommandError> {
    if value.len() < 20 || value.len() > 35 || !value.ends_with('Z') || !value.is_ascii() {
        return Err(BackendCommandError::unavailable());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn request_ids_and_library_inputs_are_bounded() {
        assert!(valid_request_id("550e8400-e29b-41d4-a716-446655440000"));
        assert!(!valid_request_id("bad id"));
        assert!(validate_identifier("550e8400-e29b-41d4-a716-446655440000").is_ok());
        assert!(validate_identifier("../library.sqlite3").is_err());
        assert!(validate_text("Project", 120, false).is_ok());
        assert!(validate_text("   ", 120, false).is_err());
    }

    #[test]
    fn readiness_requires_identity_versions_and_exact_capabilities() {
        let valid = br#"{"schema_version":1,"request_id":"one","ok":true,"result":{"status":"ready","sidecar_identity":"com.universalpromptstudio.backend","application_version":"0.2.0-alpha","protocol_version":1,"storage_schema_version":1,"capabilities":["application.readiness","library.projects.list","library.projects.create","library.projects.delete","library.prompts.list","library.prompts.create","library.prompts.get","library.prompts.update","library.prompts.delete","library.prompts.search","library.prompts.compose","library.prompts.execute-offline"]}}"#;
        let wire: WireReadiness = decode_response(valid, "one").unwrap();
        assert_eq!(validate_readiness(wire).unwrap().storage_schema_version, 1);
        assert!(decode_response::<WireReadiness>(valid, "two").is_err());
    }

    #[test]
    fn project_and_prompt_responses_are_strict_and_project_scoped() {
        let project_id = "550e8400-e29b-41d4-a716-446655440000";
        let prompt_id = "76c7169d-9e5d-4db4-bf61-856695d2a91e";
        let projects = format!(
            r#"{{"schema_version":1,"request_id":"one","ok":true,"result":{{"projects":[{{"project_id":"{project_id}","name":"UPS","description":"","created_at":"2026-08-26T00:00:00Z"}}],"has_more":false}}}}"#
        );
        let wire: WireProjectList = decode_response(projects.as_bytes(), "one").unwrap();
        assert_eq!(validate_project_list(wire).unwrap().projects.len(), 1);

        let prompts = format!(
            r#"{{"schema_version":1,"request_id":"two","ok":true,"result":{{"prompts":[{{"prompt_id":"{prompt_id}","project_id":"{project_id}","title":"First","category":"Delivery","tags":["offline"],"blocks":[{{"block_type":"goal","content":"Ship it","order":0,"enabled":true}}],"created_at":"2026-08-26T00:00:00Z","updated_at":"2026-08-26T00:00:00Z"}}],"has_more":false}}}}"#
        );
        let wire: WirePromptList = decode_response(prompts.as_bytes(), "two").unwrap();
        assert_eq!(
            validate_prompt_list(wire, project_id)
                .unwrap()
                .prompts
                .len(),
            1
        );
    }

    #[test]
    fn update_payload_maps_frontend_blocks_to_the_exact_sidecar_schema() {
        let category = Some("Delivery".to_owned());
        let tags = vec!["Offline".to_owned()];
        let blocks = vec![PromptBlockInput {
            block_type: "goal".to_owned(),
            content: "Ship it".to_owned(),
            enabled: true,
        }];
        let payload = UpdatePromptPayload {
            project_id: "550e8400-e29b-41d4-a716-446655440000",
            prompt_id: "76c7169d-9e5d-4db4-bf61-856695d2a91e",
            title: "Release",
            category: &category,
            tags: &tags,
            blocks: &blocks,
        };
        let value = serde_json::to_value(payload).unwrap();
        assert_eq!(value["blocks"][0]["block_type"], "goal");
        assert!(value["blocks"][0].get("blockType").is_none());
        let frontend: PromptBlockInput =
            serde_json::from_str(r#"{"blockType":"goal","content":"Ship it","enabled":true}"#)
                .unwrap();
        assert_eq!(frontend.block_type, "goal");
    }

    #[test]
    fn composition_and_execution_are_owned_bounded_and_offline_only() {
        let project_id = "550e8400-e29b-41d4-a716-446655440000";
        let prompt_id = "76c7169d-9e5d-4db4-bf61-856695d2a91e";
        let execution_id = "9a4da4c4-a794-48a1-98f2-99d0bf3f7902";
        let composition = validate_composition(
            WireComposition {
                project_id: project_id.to_owned(),
                prompt_id: prompt_id.to_owned(),
                title: "Architecture".to_owned(),
                final_prompt: "Role:\nArchitect".to_owned(),
                enabled_block_count: 1,
                total_block_count: 2,
                character_count: 15,
            },
            project_id,
            prompt_id,
        )
        .unwrap();
        let execution = validate_execution(
            WireExecution {
                project_id: project_id.to_owned(),
                prompt_id: prompt_id.to_owned(),
                provider_id: OFFLINE_REFERENCE_PROVIDER.to_owned(),
                provider_version: OFFLINE_REFERENCE_VERSION.to_owned(),
                execution_id: execution_id.to_owned(),
                output: "[offline provider response]\nRole:\nArchitect".to_owned(),
                input_units: 15,
                output_units: 15,
                prompt_character_count: 15,
            },
            project_id,
            prompt_id,
        )
        .unwrap();

        assert_eq!(composition.character_count, 15);
        assert_eq!(execution.provider_id, OFFLINE_REFERENCE_PROVIDER);
        assert_eq!(
            serde_json::to_value(composition).unwrap()["finalPrompt"],
            "Role:\nArchitect"
        );
        let payload = ExecutePromptPayload {
            project_id,
            prompt_id,
            provider_id: OFFLINE_REFERENCE_PROVIDER,
            confirm: true,
        };
        let value = serde_json::to_value(payload).unwrap();
        assert_eq!(value["provider_id"], OFFLINE_REFERENCE_PROVIDER);
        assert!(value.get("providerId").is_none());
        assert!(
            validate_execution(
                WireExecution {
                    project_id: project_id.to_owned(),
                    prompt_id: prompt_id.to_owned(),
                    provider_id: "dummy".to_owned(),
                    provider_version: OFFLINE_REFERENCE_VERSION.to_owned(),
                    execution_id: execution_id.to_owned(),
                    output: "unsafe".to_owned(),
                    input_units: 1,
                    output_units: 1,
                    prompt_character_count: 1,
                },
                project_id,
                prompt_id,
            )
            .is_err()
        );
    }

    #[test]
    fn backend_errors_are_allowlisted_and_python_messages_are_not_exposed() {
        let execution = br#"{"schema_version":1,"request_id":"one","ok":false,"error":{"code":"execution.failed","message":"secret"}}"#;
        let error = decode_response::<WireReadiness>(execution, "one").unwrap_err();
        assert_eq!(error.code, "execution.failed");
        assert_eq!(error.message, "Offline prompt execution failed safely.");
        assert!(!error.message.contains("secret"));
        let invalid = br#"{"schema_version":1,"request_id":"one","ok":false,"error":{"code":"ipc.invalid_payload","message":"secret"}}"#;
        let error = decode_response::<WireReadiness>(invalid, "one").unwrap_err();
        assert_eq!(error.code, "library.invalid_input");
        assert!(!error.message.contains("secret"));

        let unknown = br#"{"schema_version":1,"request_id":"one","ok":false,"error":{"code":"unexpected","message":"secret"}}"#;
        assert_eq!(
            decode_response::<WireReadiness>(unknown, "one")
                .unwrap_err()
                .code,
            "backend.unavailable"
        );
    }
}
