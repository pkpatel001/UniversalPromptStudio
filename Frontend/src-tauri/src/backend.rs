//! Fixed, correlated lifecycle bridge to the A-001.1 Python application process.

use serde::{Deserialize, Serialize};
use std::fmt;
use std::io::Write;
#[cfg(debug_assertions)]
use std::io::{BufRead, BufReader};
#[cfg(debug_assertions)]
use std::path::PathBuf;
use std::process::{Child, ChildStdin};
#[cfg(debug_assertions)]
use std::process::{Command, Stdio};
#[cfg(debug_assertions)]
use std::sync::mpsc;
use std::sync::mpsc::Receiver;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

const IPC_PROTOCOL_VERSION: u32 = 1;
const MAX_IPC_MESSAGE_BYTES: usize = 16_384;
const RESPONSE_TIMEOUT: Duration = Duration::from_secs(3);
const READINESS_COMMAND: &str = "application.readiness";

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
    child: Child,
    input: Option<ChildStdin>,
    output: Receiver<Result<Vec<u8>, ()>>,
}

impl BackendProcess {
    #[cfg(debug_assertions)]
    fn spawn_development() -> Result<Self, BackendCommandError> {
        let project_root = development_project_root()?;
        let mut command = Command::new("python");
        command
            .args(["-m", "Backend.ipc"])
            .current_dir(project_root)
            .env("PYTHONDONTWRITEBYTECODE", "1")
            .env("PYTHONUNBUFFERED", "1")
            .env("PYTHONUTF8", "1")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x0800_0000);
        }
        let mut child = command
            .spawn()
            .map_err(|_| BackendCommandError::unavailable())?;
        let input = child
            .stdin
            .take()
            .ok_or_else(BackendCommandError::unavailable)?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(BackendCommandError::unavailable)?;
        let (sender, output) = mpsc::channel();
        thread::spawn(move || {
            for line in BufReader::new(stdout).split(b'\n') {
                let value = match line {
                    Ok(value) if value.len() <= MAX_IPC_MESSAGE_BYTES => Ok(value),
                    _ => Err(()),
                };
                let failed = value.is_err();
                if sender.send(value).is_err() || failed {
                    break;
                }
            }
        });
        Ok(Self {
            child,
            input: Some(input),
            output,
        })
    }

    #[cfg(not(debug_assertions))]
    fn spawn_development() -> Result<Self, BackendCommandError> {
        Err(BackendCommandError::unavailable())
    }

    fn readiness(&mut self, request_id: &str) -> Result<BackendReadiness, BackendCommandError> {
        let request = WireRequest {
            schema_version: IPC_PROTOCOL_VERSION,
            request_id,
            command: READINESS_COMMAND,
            payload: WirePayload::default(),
        };
        let encoded =
            serde_json::to_vec(&request).map_err(|_| BackendCommandError::unavailable())?;
        if encoded.len() > MAX_IPC_MESSAGE_BYTES {
            return Err(BackendCommandError::new(
                "backend.invalid_request",
                "The backend request is too large.",
            ));
        }
        let input = self
            .input
            .as_mut()
            .ok_or_else(BackendCommandError::unavailable)?;
        input
            .write_all(&encoded)
            .and_then(|_| input.write_all(b"\n"))
            .and_then(|_| input.flush())
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
        self.input.take();
        let deadline = Instant::now() + Duration::from_millis(500);
        while Instant::now() < deadline {
            match self.child.try_wait() {
                Ok(Some(_)) => return,
                Ok(None) => thread::sleep(Duration::from_millis(20)),
                Err(_) => break,
            }
        }
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

#[derive(Clone, Default)]
pub struct BackendManager {
    process: Arc<Mutex<Option<BackendProcess>>>,
}

impl BackendManager {
    pub fn new() -> Self {
        Self::default()
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
            *process = Some(BackendProcess::spawn_development()?);
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

#[cfg(debug_assertions)]
fn development_project_root() -> Result<PathBuf, BackendCommandError> {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .map_err(|_| BackendCommandError::unavailable())
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
            || result.protocol_version != IPC_PROTOCOL_VERSION
            || result.capabilities != [READINESS_COMMAND]
            || result.application_version.is_empty()
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
    fn response_parser_requires_exact_correlation_and_contract() {
        let valid = br#"{"schema_version":1,"request_id":"one","ok":true,"result":{"status":"ready","application_version":"0.2.0-alpha","protocol_version":1,"capabilities":["application.readiness"]}}"#;
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
        let extra = br#"{"schema_version":1,"request_id":"one","ok":true,"result":{"status":"ready","application_version":"0.2.0-alpha","protocol_version":1,"capabilities":["application.readiness"]},"extra":true}"#;
        assert!(parse_readiness_response(extra, "one").is_err());

        let backend_error = br#"{"schema_version":1,"request_id":"one","ok":false,"error":{"code":"ipc.internal_error","message":"Untrusted backend detail."}}"#;
        let collapsed = parse_readiness_response(backend_error, "one").unwrap_err();
        assert_eq!(collapsed.code, "backend.unavailable");
        assert_eq!(
            collapsed.message,
            "The local application backend is unavailable."
        );
    }

    #[test]
    fn one_python_process_serves_multiple_correlated_requests() {
        let mut process = BackendProcess::spawn_development().unwrap();
        let process_id = process.child.id();
        let first = process.readiness("rust-one").unwrap();
        let second = process.readiness("rust-two").unwrap();

        assert_eq!(process.child.id(), process_id);
        assert_eq!(first.status, "ready");
        assert_eq!(second.application_version, "0.2.0-alpha");
    }
}
