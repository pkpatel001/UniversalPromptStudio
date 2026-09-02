//! Strict A-007 bridge for settings, portable items, and redacted diagnostics.

use crate::backend::{BackendCommandError, BackendManager};
use serde::{Deserialize, Serialize};

const SETTINGS_GET_COMMAND: &str = "application.settings.get";
const SETTINGS_SAVE_COMMAND: &str = "application.settings.save";
const PORTABILITY_EXPORT_COMMAND: &str = "portability.export";
const PORTABILITY_PREVIEW_COMMAND: &str = "portability.preview";
const PORTABILITY_IMPORT_COMMAND: &str = "portability.import";
const DIAGNOSTICS_COMMAND: &str = "diagnostics.snapshot";
const SUPPORT_PREVIEW_COMMAND: &str = "diagnostics.support.preview";
const SUPPORT_EXPORT_COMMAND: &str = "diagnostics.support.export";
const MAX_DOCUMENT_CHARACTERS: usize = 10_000;
const MAX_SUPPORT_DOCUMENT_CHARACTERS: usize = 12_500;
const REDACTIONS: [&str; 6] = [
    "credentials",
    "prompt-content",
    "workflow-definitions-and-runtime-values",
    "filesystem-paths",
    "environment-values",
    "extension-code-and-contributions",
];

#[derive(Debug, Serialize)]
struct EmptyPayload {}

#[derive(Debug, Serialize)]
struct SettingsPayload {
    onboarding_completed: bool,
    compact_layout: bool,
    reduce_motion: bool,
    confirm: bool,
}

#[derive(Debug, Serialize)]
struct ExportPayload {
    kind: String,
    item_id: String,
    project_id: Option<String>,
}

#[derive(Debug, Serialize)]
struct PreviewPayload {
    document: String,
    target_project_id: Option<String>,
}

#[derive(Debug, Serialize)]
struct ImportPayload {
    document: String,
    target_project_id: Option<String>,
    expected_sha256: String,
    resolution: String,
    confirm: bool,
}

#[derive(Debug, Serialize)]
struct SupportExportPayload {
    expected_sha256: String,
    acknowledge_redaction_review: bool,
    confirm: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct ApplicationSettings {
    schema_version: u32,
    onboarding_completed: bool,
    compact_layout: bool,
    reduce_motion: bool,
    language: String,
    automatic_updates: String,
    telemetry: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct PortableExport {
    schema_version: u32,
    kind: String,
    item_id: String,
    title: String,
    filename: String,
    document: String,
    document_sha256: String,
    document_characters: usize,
    excluded: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct PortablePreview {
    schema_version: u32,
    kind: String,
    item_id: String,
    title: String,
    target_project_id: Option<String>,
    document_sha256: String,
    document_characters: usize,
    conflict_state: String,
    allowed_resolutions: Vec<String>,
    changes: Vec<String>,
    excluded: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct PortableImportResult {
    kind: String,
    item_id: String,
    title: String,
    target_project_id: Option<String>,
    applied: bool,
    status: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct DiagnosticApplication {
    version: String,
    protocol_version: u32,
    storage_schema_version: u32,
    platform: String,
    package: String,
    signed: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct DiagnosticLibrary {
    project_count: usize,
    prompt_count: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct DiagnosticWorkflows {
    definition_count: usize,
    operation_count: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct DiagnosticProvider {
    provider_id: String,
    available: bool,
    credential_state: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct DiagnosticCustomizations {
    theme_count: usize,
    active_theme_count: usize,
    extension_count: usize,
    active_extension_count: usize,
    issue_count: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct DiagnosticPreferences {
    onboarding_completed: bool,
    compact_layout: bool,
    reduce_motion: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct DiagnosticsSnapshot {
    schema_version: u32,
    application: DiagnosticApplication,
    library: DiagnosticLibrary,
    workflows: DiagnosticWorkflows,
    providers: Vec<DiagnosticProvider>,
    customizations: DiagnosticCustomizations,
    preferences: DiagnosticPreferences,
    redactions: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct SupportPreview {
    schema_version: u32,
    format: String,
    included_sections: Vec<String>,
    redactions: Vec<String>,
    contains_credentials: bool,
    contains_user_content: bool,
    document_sha256: String,
    document_characters: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct SupportExport {
    filename: String,
    document: String,
    document_sha256: String,
    document_characters: usize,
    contains_credentials: bool,
    contains_user_content: bool,
}

#[tauri::command]
pub async fn application_settings(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
) -> Result<ApplicationSettings, BackendCommandError> {
    request(
        state,
        request_id,
        SETTINGS_GET_COMMAND,
        EmptyPayload {},
        validate_settings,
    )
    .await
}

#[tauri::command]
pub async fn application_settings_save(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    onboarding_completed: bool,
    compact_layout: bool,
    reduce_motion: bool,
    confirm: bool,
) -> Result<ApplicationSettings, BackendCommandError> {
    require_confirmation(confirm)?;
    request(
        state,
        request_id,
        SETTINGS_SAVE_COMMAND,
        SettingsPayload {
            onboarding_completed,
            compact_layout,
            reduce_motion,
            confirm,
        },
        validate_settings,
    )
    .await
}

#[tauri::command]
pub async fn portability_export(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    kind: String,
    item_id: String,
    project_id: Option<String>,
) -> Result<PortableExport, BackendCommandError> {
    validate_item_target(&kind, &item_id, project_id.as_deref())?;
    request(
        state,
        request_id,
        PORTABILITY_EXPORT_COMMAND,
        ExportPayload {
            kind,
            item_id,
            project_id,
        },
        validate_export,
    )
    .await
}

#[tauri::command]
pub async fn portability_preview(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    document: String,
    target_project_id: Option<String>,
) -> Result<PortablePreview, BackendCommandError> {
    validate_document(&document)?;
    validate_optional_uuid(target_project_id.as_deref())?;
    request(
        state,
        request_id,
        PORTABILITY_PREVIEW_COMMAND,
        PreviewPayload {
            document,
            target_project_id,
        },
        validate_preview,
    )
    .await
}

#[tauri::command]
#[allow(clippy::too_many_arguments)]
pub async fn portability_import(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    document: String,
    target_project_id: Option<String>,
    expected_sha256: String,
    resolution: String,
    confirm: bool,
) -> Result<PortableImportResult, BackendCommandError> {
    validate_document(&document)?;
    validate_optional_uuid(target_project_id.as_deref())?;
    validate_sha256(&expected_sha256)?;
    if !matches!(resolution.as_str(), "create" | "skip" | "replace") {
        return Err(invalid("The portable conflict resolution is invalid."));
    }
    require_confirmation(confirm)?;
    request(
        state,
        request_id,
        PORTABILITY_IMPORT_COMMAND,
        ImportPayload {
            document,
            target_project_id,
            expected_sha256,
            resolution,
            confirm,
        },
        validate_import,
    )
    .await
}

#[tauri::command]
pub async fn diagnostics_snapshot(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
) -> Result<DiagnosticsSnapshot, BackendCommandError> {
    request(
        state,
        request_id,
        DIAGNOSTICS_COMMAND,
        EmptyPayload {},
        validate_diagnostics,
    )
    .await
}

#[tauri::command]
pub async fn support_preview(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
) -> Result<SupportPreview, BackendCommandError> {
    request(
        state,
        request_id,
        SUPPORT_PREVIEW_COMMAND,
        EmptyPayload {},
        validate_support_preview,
    )
    .await
}

#[tauri::command]
pub async fn support_export(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    expected_sha256: String,
    acknowledge_redaction_review: bool,
    confirm: bool,
) -> Result<SupportExport, BackendCommandError> {
    validate_sha256(&expected_sha256)?;
    if !acknowledge_redaction_review || !confirm {
        return Err(invalid("Support export requires review and confirmation."));
    }
    let reviewed_sha256 = expected_sha256.clone();
    let value = request(
        state,
        request_id,
        SUPPORT_EXPORT_COMMAND,
        SupportExportPayload {
            expected_sha256,
            acknowledge_redaction_review,
            confirm,
        },
        validate_support_export,
    )
    .await?;
    if value.document_sha256 != reviewed_sha256 {
        return Err(BackendCommandError::unavailable());
    }
    Ok(value)
}

async fn request<P, T>(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    command: &'static str,
    payload: P,
    validate: fn(T) -> Result<T, BackendCommandError>,
) -> Result<T, BackendCommandError>
where
    P: Serialize + Send + 'static,
    T: for<'de> Deserialize<'de> + Send + 'static,
{
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let value: T = manager.request(&request_id, command, payload)?;
        validate(value)
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

fn validate_settings(
    value: ApplicationSettings,
) -> Result<ApplicationSettings, BackendCommandError> {
    if value.schema_version != 1
        || value.language != "en"
        || value.automatic_updates != "unsupported"
        || value.telemetry != "disabled"
    {
        return Err(BackendCommandError::unavailable());
    }
    Ok(value)
}

fn validate_export(value: PortableExport) -> Result<PortableExport, BackendCommandError> {
    validate_kind_and_id(&value.kind, &value.item_id)?;
    validate_text(&value.title, 120)?;
    validate_filename(&value.filename)?;
    validate_document(&value.document)?;
    validate_sha256(&value.document_sha256)?;
    if value.schema_version != 1
        || value.document_characters != value.document.chars().count()
        || value.excluded != excluded()
    {
        return Err(BackendCommandError::unavailable());
    }
    Ok(value)
}

fn validate_preview(value: PortablePreview) -> Result<PortablePreview, BackendCommandError> {
    validate_kind_and_id(&value.kind, &value.item_id)?;
    validate_text(&value.title, 120)?;
    validate_optional_uuid(value.target_project_id.as_deref())?;
    validate_sha256(&value.document_sha256)?;
    if value.schema_version != 1
        || value.document_characters == 0
        || value.document_characters > MAX_DOCUMENT_CHARACTERS
        || !matches!(
            value.conflict_state.as_str(),
            "none" | "same-target" | "different-project"
        )
        || value.allowed_resolutions.is_empty()
        || value.allowed_resolutions.len() > 2
        || value
            .allowed_resolutions
            .iter()
            .any(|item| !matches!(item.as_str(), "create" | "skip" | "replace"))
        || value.changes != vec![format!("{}-definition", value.kind)]
        || value.excluded != excluded()
    {
        return Err(BackendCommandError::unavailable());
    }
    Ok(value)
}

fn validate_import(
    value: PortableImportResult,
) -> Result<PortableImportResult, BackendCommandError> {
    validate_kind_and_id(&value.kind, &value.item_id)?;
    validate_text(&value.title, 120)?;
    validate_optional_uuid(value.target_project_id.as_deref())?;
    if !matches!(value.status.as_str(), "created" | "replaced" | "skipped")
        || value.applied != (value.status != "skipped")
    {
        return Err(BackendCommandError::unavailable());
    }
    Ok(value)
}

fn validate_diagnostics(
    value: DiagnosticsSnapshot,
) -> Result<DiagnosticsSnapshot, BackendCommandError> {
    validate_text(&value.application.version, 64)?;
    if value.schema_version != 1
        || value.application.protocol_version != 1
        || value.application.storage_schema_version != 1
        || value.application.platform != "windows-x64"
        || value.application.package != "nsis-current-user"
        || value.providers.len() > 20
        || value.redactions != redactions()
        || value.customizations.active_theme_count > value.customizations.theme_count
        || value.customizations.active_extension_count > value.customizations.extension_count
    {
        return Err(BackendCommandError::unavailable());
    }
    for provider in &value.providers {
        validate_qualified_id(&provider.provider_id)?;
        validate_text(&provider.credential_state, 40)?;
    }
    Ok(value)
}

fn validate_support_preview(value: SupportPreview) -> Result<SupportPreview, BackendCommandError> {
    validate_sha256(&value.document_sha256)?;
    if value.schema_version != 1
        || value.format != "ups-redacted-support"
        || value.included_sections
            != vec![
                "application",
                "library-counts",
                "workflow-counts",
                "provider-availability",
                "customization-counts",
                "application-preferences",
            ]
        || value.redactions != redactions()
        || value.contains_credentials
        || value.contains_user_content
        || value.document_characters == 0
        || value.document_characters > MAX_SUPPORT_DOCUMENT_CHARACTERS
    {
        return Err(BackendCommandError::unavailable());
    }
    Ok(value)
}

fn validate_support_export(value: SupportExport) -> Result<SupportExport, BackendCommandError> {
    validate_filename(&value.filename)?;
    validate_sha256(&value.document_sha256)?;
    if value.document.is_empty()
        || value.document.chars().count() != value.document_characters
        || value.document_characters > MAX_SUPPORT_DOCUMENT_CHARACTERS
        || value.contains_credentials
        || value.contains_user_content
    {
        return Err(BackendCommandError::unavailable());
    }
    Ok(value)
}

fn validate_item_target(
    kind: &str,
    item_id: &str,
    project_id: Option<&str>,
) -> Result<(), BackendCommandError> {
    validate_kind_and_id(kind, item_id)?;
    if (kind == "prompt" && project_id.is_none()) || (kind == "workflow" && project_id.is_some()) {
        return Err(invalid("The portable item target is invalid."));
    }
    validate_optional_uuid(project_id)
}

fn validate_kind_and_id(kind: &str, item_id: &str) -> Result<(), BackendCommandError> {
    match kind {
        "prompt" => validate_uuid(item_id),
        "workflow" => validate_qualified_id(item_id),
        _ => Err(invalid("The portable item kind is invalid.")),
    }
}

fn validate_document(value: &str) -> Result<(), BackendCommandError> {
    if value.is_empty()
        || value.chars().count() > MAX_DOCUMENT_CHARACTERS
        || serde_json::from_str::<serde_json::Value>(value).is_err()
    {
        return Err(invalid("The portable document is invalid or too large."));
    }
    Ok(())
}

fn validate_filename(value: &str) -> Result<(), BackendCommandError> {
    if value.is_empty()
        || value.len() > 180
        || !value.ends_with(".json")
        || value.chars().any(|character| {
            !(character.is_ascii_alphanumeric() || matches!(character, '-' | '_' | '.'))
        })
    {
        return Err(BackendCommandError::unavailable());
    }
    Ok(())
}

fn validate_optional_uuid(value: Option<&str>) -> Result<(), BackendCommandError> {
    value.map_or(Ok(()), validate_uuid)
}

fn validate_uuid(value: &str) -> Result<(), BackendCommandError> {
    let bytes = value.as_bytes();
    if bytes.len() != 36
        || [8, 13, 18, 23].iter().any(|index| bytes[*index] != b'-')
        || bytes
            .iter()
            .enumerate()
            .any(|(index, byte)| ![8, 13, 18, 23].contains(&index) && !byte.is_ascii_hexdigit())
        || value.to_ascii_lowercase() != value
    {
        return Err(invalid("The portable UUID is invalid."));
    }
    Ok(())
}

fn validate_qualified_id(value: &str) -> Result<(), BackendCommandError> {
    if value.len() > 128
        || !value.contains('.')
        || value.split('.').any(|part| {
            part.is_empty()
                || !part.as_bytes()[0].is_ascii_lowercase()
                || part.bytes().any(|byte| {
                    !(byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-')
                })
        })
    {
        return Err(invalid("The portable workflow identity is invalid."));
    }
    Ok(())
}

fn validate_sha256(value: &str) -> Result<(), BackendCommandError> {
    if value.len() != 64
        || value
            .bytes()
            .any(|byte| !byte.is_ascii_hexdigit() || byte.is_ascii_uppercase())
    {
        return Err(invalid("The reviewed SHA-256 is invalid."));
    }
    Ok(())
}

fn validate_text(value: &str, maximum: usize) -> Result<(), BackendCommandError> {
    if value.is_empty() || value.trim() != value || value.chars().count() > maximum {
        return Err(BackendCommandError::unavailable());
    }
    Ok(())
}

fn require_confirmation(value: bool) -> Result<(), BackendCommandError> {
    if !value {
        return Err(invalid("The operation requires explicit confirmation."));
    }
    Ok(())
}

fn excluded() -> Vec<String> {
    vec!["credentials", "execution-history", "extension-approval"]
        .into_iter()
        .map(String::from)
        .collect()
}

fn redactions() -> Vec<String> {
    REDACTIONS.into_iter().map(String::from).collect()
}

fn invalid(message: &str) -> BackendCommandError {
    BackendCommandError::invalid_request(message)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn portable_inputs_are_bounded_and_targeted() {
        assert!(
            validate_item_target(
                "prompt",
                "550e8400-e29b-41d4-a716-446655440000",
                Some("76c7169d-9e5d-4db4-bf61-856695d2a91e")
            )
            .is_ok()
        );
        assert!(validate_item_target("workflow", "ups.user-flow", None).is_ok());
        assert!(
            validate_item_target(
                "workflow",
                "ups.user-flow",
                Some("76c7169d-9e5d-4db4-bf61-856695d2a91e")
            )
            .is_err()
        );
        assert!(validate_document("{}").is_ok());
        assert!(validate_document(&"x".repeat(MAX_DOCUMENT_CHARACTERS + 1)).is_err());
    }

    #[test]
    fn settings_policy_is_fixed() {
        let value = ApplicationSettings {
            schema_version: 1,
            onboarding_completed: false,
            compact_layout: false,
            reduce_motion: false,
            language: "en".into(),
            automatic_updates: "unsupported".into(),
            telemetry: "disabled".into(),
        };
        assert!(validate_settings(value).is_ok());
    }
}
