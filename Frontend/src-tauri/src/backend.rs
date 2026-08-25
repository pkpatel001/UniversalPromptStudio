//! Fixed, correlated lifecycle bridge to the bundled A-001.2 application sidecar.

use serde::{Deserialize, Serialize};
use std::fmt;
use std::sync::mpsc::{self, Receiver};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri::AppHandle;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};

const IPC_PROTOCOL_VERSION: u32 = 1;
const MAX_IPC_MESSAGE_BYTES: usize = 16_384;
const RESPONSE_TIMEOUT: Duration = Duration::from_secs(3);
const READINESS_COMMAND: &str = "application.readiness";
const SIDECAR_IDENTITY: &str = "com.universalpromptstudio.backend";
const SIDECAR_NAME: &str = "universal-prompt-studio-backend";

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BackendReadiness {
    status: String,
    application_version: String,
    protocol_version: u32,
    capabilities: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct BackendCommandError {
    code: String,
    message: String,
}

impl BackendCommandError {
    fn new(code: &str, message: &str) -> Self {
        Self {
            code: code.to_owned(),
            message: message.to_owned(),
        }
    }

    fn unavailable() -> Self {
        Self::new(
            "backend.unavailable",
            "The local application backend is unavailable.",
        )
    }
}

impl fmt::Display for BackendCommandError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}", self.message)
    }
}

#[derive(Debug, Serialize)]
struct WireRequest<'a> {
    schema_version: u32,
    request_id: &'a str,
    command: &'static str,
    payload: WirePayload,
}

#[derive(Debug, Default, Serialize)]
struct WirePayload {}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireResponse {
    schema_version: u32,
    request_id: String,
    ok: bool,
    #[serde(default)]
    result: Option<WireReadiness>,
    #[serde(default)]
    error: Option<WireError>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WireReadiness {
    status: String,
    sidecar_identity: String,
    application_version: String,
    protocol_version: u32,
    capabilities: Vec<String>,
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
        let mut command = app
            .shell()
            .sidecar(SIDECAR_NAME)
            .map_err(|_| BackendCommandError::unavailable())?
            .env_clear();
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

    fn readiness(&mut self, request_id: &str) -> Result<BackendReadiness, BackendCommandError> {
        let request = WireRequest {
            schema_version: IPC_PROTOCOL_VERSION,
            request_id,
            command: READINESS_COMMAND,
            payload: WirePayload::default(),
        };
        let mut encoded =
            serde_json::to_vec(&request).map_err(|_| BackendCommandError::unavailable())?;
        if encoded.len() > MAX_IPC_MESSAGE_BYTES {
            return Err(BackendCommandError::new(
                "backend.invalid_request",
                "The backend request is too large.",
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
        parse_readiness_response(&line, request_id)
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

    fn readiness(&self, request_id: &str) -> Result<BackendReadiness, BackendCommandError> {
        if !valid_request_id(request_id) {
            return Err(BackendCommandError::new(
                "backend.invalid_request",
                "The backend request identifier is invalid.",
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
            .readiness(request_id);
        if result.is_err() {
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
    tauri::async_runtime::spawn_blocking(move || manager.readiness(&request_id))
        .await
        .map_err(|_| BackendCommandError::unavailable())?
}

fn valid_request_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 64
        && value.bytes().enumerate().all(|(index, byte)| {
            byte.is_ascii_alphanumeric() || (index > 0 && matches!(byte, b'.' | b'_' | b':' | b'-'))
        })
}

fn parse_readiness_response(
    line: &[u8],
    expected_request_id: &str,
) -> Result<BackendReadiness, BackendCommandError> {
    let response: WireResponse =
        serde_json::from_slice(line).map_err(|_| BackendCommandError::unavailable())?;
    if response.schema_version != IPC_PROTOCOL_VERSION || response.request_id != expected_request_id
    {
        return Err(BackendCommandError::unavailable());
    }
    if response.ok {
        if response.error.is_some() {
            return Err(BackendCommandError::unavailable());
        }
        let result = response
            .result
            .ok_or_else(BackendCommandError::unavailable)?;
        if result.status != "ready"
            || result.sidecar_identity != SIDECAR_IDENTITY
            || result.application_version != env!("CARGO_PKG_VERSION")
            || result.protocol_version != IPC_PROTOCOL_VERSION
            || result.capabilities != [READINESS_COMMAND]
        {
            return Err(BackendCommandError::unavailable());
        }
        return Ok(BackendReadiness {
            status: result.status,
            application_version: result.application_version,
            protocol_version: result.protocol_version,
            capabilities: result.capabilities,
        });
    }
    if response.result.is_some() {
        return Err(BackendCommandError::unavailable());
    }
    let error = response
        .error
        .ok_or_else(BackendCommandError::unavailable)?;
    if error.code.is_empty() || error.code.len() > 64 || error.message.len() > 256 {
        return Err(BackendCommandError::unavailable());
    }
    Err(BackendCommandError::unavailable())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn request_ids_are_bounded_and_portable() {
        assert!(valid_request_id("550e8400-e29b-41d4-a716-446655440000"));
        assert!(valid_request_id("request_1:probe.ready"));
        assert!(!valid_request_id(""));
        assert!(!valid_request_id("bad id"));
        assert!(!valid_request_id("-leading"));
        assert!(!valid_request_id(&"x".repeat(65)));
    }

    #[test]
    fn response_parser_requires_identity_version_protocol_and_correlation() {
        let valid = br#"{"schema_version":1,"request_id":"one","ok":true,"result":{"status":"ready","sidecar_identity":"com.universalpromptstudio.backend","application_version":"0.2.0-alpha","protocol_version":1,"capabilities":["application.readiness"]}}"#;
        assert_eq!(
            parse_readiness_response(valid, "one").unwrap(),
            BackendReadiness {
                status: "ready".to_owned(),
                application_version: "0.2.0-alpha".to_owned(),
                protocol_version: 1,
                capabilities: vec![READINESS_COMMAND.to_owned()],
            }
        );
        assert!(parse_readiness_response(valid, "two").is_err());

        let wrong_identity = br#"{"schema_version":1,"request_id":"one","ok":true,"result":{"status":"ready","sidecar_identity":"example.invalid","application_version":"0.2.0-alpha","protocol_version":1,"capabilities":["application.readiness"]}}"#;
        assert!(parse_readiness_response(wrong_identity, "one").is_err());
        let wrong_version = br#"{"schema_version":1,"request_id":"one","ok":true,"result":{"status":"ready","sidecar_identity":"com.universalpromptstudio.backend","application_version":"0.2.1","protocol_version":1,"capabilities":["application.readiness"]}}"#;
        assert!(parse_readiness_response(wrong_version, "one").is_err());

        let backend_error = br#"{"schema_version":1,"request_id":"one","ok":false,"error":{"code":"ipc.internal_error","message":"Untrusted backend detail."}}"#;
        let collapsed = parse_readiness_response(backend_error, "one").unwrap_err();
        assert_eq!(collapsed.code, "backend.unavailable");
        assert_eq!(
            collapsed.message,
            "The local application backend is unavailable."
        );
    }
}
