//! Strict A-006 bridge for managed themes and trusted session extensions.

use crate::backend::{BackendCommandError, BackendManager};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

const CUSTOMIZATION_CATALOG_COMMAND: &str = "customizations.catalog";
const THEME_INSTALL_COMMAND: &str = "themes.install";
const THEME_LIFECYCLE_COMMAND: &str = "themes.lifecycle";
const EXTENSION_ACTIVATE_COMMAND: &str = "extensions.activate";
const EXTENSION_DEACTIVATE_COMMAND: &str = "extensions.deactivate";
const MAX_ITEMS: usize = 20;
const MAX_ISSUES: usize = 10;
const TOKEN_NAMES: [&str; 11] = [
    "canvas",
    "surface",
    "surface-muted",
    "text",
    "text-muted",
    "border",
    "primary",
    "primary-text",
    "sidebar",
    "sidebar-text",
    "focus",
];

#[derive(Debug, Serialize)]
struct EmptyPayload {}

#[derive(Debug, Serialize)]
struct ThemeInstallPayload<'a> {
    package_filename: &'a str,
    approved_sha256: &'a str,
    acknowledge_external_theme: bool,
    confirm: bool,
}

#[derive(Debug, Serialize)]
struct ThemeLifecyclePayload<'a> {
    theme_id: &'a str,
    version: &'a str,
    action: &'a str,
    approved_package_sha256: &'a str,
    acknowledge_lifecycle_change: bool,
    confirm: bool,
}

#[derive(Debug, Serialize)]
struct ExtensionActivationPayload<'a> {
    plugin_id: &'a str,
    version: &'a str,
    directory_sha256: &'a str,
    acknowledge_full_trust: bool,
    confirm: bool,
}

#[derive(Debug, Serialize)]
struct ExtensionDeactivationPayload<'a> {
    plugin_id: &'a str,
    version: &'a str,
    directory_sha256: &'a str,
    confirm: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct CustomizationBoundaries {
    theme_install: String,
    theme_remove: String,
    extension_install: String,
    extension_remove: String,
    extension_runtime: String,
    remote_discovery: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct ThemeSelection {
    theme_id: String,
    theme_name: String,
    version: String,
    appearance: String,
    tokens: BTreeMap<String, String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct ManagedTheme {
    theme_id: String,
    name: String,
    version: String,
    description: String,
    sdk_version: u32,
    state: String,
    origin: String,
    compatibility: String,
    trust_state: String,
    package_sha256: String,
    source_label: String,
    appearances: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct ThemePackage {
    filename: String,
    theme_id: Option<String>,
    name: Option<String>,
    version: Option<String>,
    package_sha256: Option<String>,
    compatibility: String,
    trust_state: String,
    valid: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct ManagedExtension {
    plugin_id: String,
    name: String,
    version: String,
    description: String,
    sdk_version: u32,
    origin: String,
    compatibility: String,
    trust_state: String,
    runtime_state: String,
    directory_sha256: Option<String>,
    capabilities: Vec<String>,
    permissions: Vec<String>,
    restart_behavior: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct CustomizationIssue {
    area: String,
    code: String,
    message: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct CustomizationCatalog {
    schema_version: u32,
    boundaries: CustomizationBoundaries,
    theme_selections: Vec<ThemeSelection>,
    themes: Vec<ManagedTheme>,
    theme_packages: Vec<ThemePackage>,
    extensions: Vec<ManagedExtension>,
    issues: Vec<CustomizationIssue>,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct ThemeLifecycleResult {
    action: String,
    applied: bool,
    theme_id: Option<String>,
    version: Option<String>,
    package_sha256: Option<String>,
    state: Option<String>,
    issues: Vec<CustomizationIssue>,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields, rename_all(serialize = "camelCase"))]
pub struct ExtensionRuntimeResult {
    plugin_id: String,
    version: String,
    directory_sha256: String,
    runtime_state: String,
    contribution_count: usize,
    error: Option<String>,
    restart_behavior: String,
}

#[tauri::command]
pub async fn customization_catalog(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
) -> Result<CustomizationCatalog, BackendCommandError> {
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let value: CustomizationCatalog =
            manager.request(&request_id, CUSTOMIZATION_CATALOG_COMMAND, EmptyPayload {})?;
        validate_catalog(value)
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn theme_install(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    package_filename: String,
    approved_sha256: String,
    acknowledge_external_theme: bool,
    confirm: bool,
) -> Result<ThemeLifecycleResult, BackendCommandError> {
    validate_package_filename(&package_filename)?;
    validate_sha256(&approved_sha256)?;
    validate_confirmation(confirm)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let value: ThemeLifecycleResult = manager.request(
            &request_id,
            THEME_INSTALL_COMMAND,
            ThemeInstallPayload {
                package_filename: &package_filename,
                approved_sha256: &approved_sha256,
                acknowledge_external_theme,
                confirm,
            },
        )?;
        validate_theme_result(value, "install")
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
#[allow(clippy::too_many_arguments)]
pub async fn theme_lifecycle(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    theme_id: String,
    version: String,
    action: String,
    approved_package_sha256: String,
    acknowledge_lifecycle_change: bool,
    confirm: bool,
) -> Result<ThemeLifecycleResult, BackendCommandError> {
    validate_qualified_id(&theme_id)?;
    validate_version(&version)?;
    validate_sha256(&approved_package_sha256)?;
    if !matches!(action.as_str(), "disable" | "restore") {
        return Err(BackendCommandError::invalid_request(
            "The theme lifecycle action is invalid.",
        ));
    }
    validate_confirmation(confirm)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let value: ThemeLifecycleResult = manager.request(
            &request_id,
            THEME_LIFECYCLE_COMMAND,
            ThemeLifecyclePayload {
                theme_id: &theme_id,
                version: &version,
                action: &action,
                approved_package_sha256: &approved_package_sha256,
                acknowledge_lifecycle_change,
                confirm,
            },
        )?;
        validate_theme_result(value, &action)
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn extension_activate(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    plugin_id: String,
    version: String,
    directory_sha256: String,
    acknowledge_full_trust: bool,
    confirm: bool,
) -> Result<ExtensionRuntimeResult, BackendCommandError> {
    validate_extension_input(&plugin_id, &version, &directory_sha256, confirm)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let value: ExtensionRuntimeResult = manager.request(
            &request_id,
            EXTENSION_ACTIVATE_COMMAND,
            ExtensionActivationPayload {
                plugin_id: &plugin_id,
                version: &version,
                directory_sha256: &directory_sha256,
                acknowledge_full_trust,
                confirm,
            },
        )?;
        validate_extension_result(value, &plugin_id, &version, &directory_sha256)
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

#[tauri::command]
pub async fn extension_deactivate(
    state: tauri::State<'_, BackendManager>,
    request_id: String,
    plugin_id: String,
    version: String,
    directory_sha256: String,
    confirm: bool,
) -> Result<ExtensionRuntimeResult, BackendCommandError> {
    validate_extension_input(&plugin_id, &version, &directory_sha256, confirm)?;
    let manager = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let value: ExtensionRuntimeResult = manager.request(
            &request_id,
            EXTENSION_DEACTIVATE_COMMAND,
            ExtensionDeactivationPayload {
                plugin_id: &plugin_id,
                version: &version,
                directory_sha256: &directory_sha256,
                confirm,
            },
        )?;
        validate_extension_result(value, &plugin_id, &version, &directory_sha256)
    })
    .await
    .map_err(|_| BackendCommandError::unavailable())?
}

fn validate_catalog(
    value: CustomizationCatalog,
) -> Result<CustomizationCatalog, BackendCommandError> {
    if value.schema_version != 1
        || value.boundaries.theme_install != "managed-inbox-only"
        || value.boundaries.theme_remove != "unsupported"
        || value.boundaries.extension_install != "unsupported"
        || value.boundaries.extension_remove != "unsupported"
        || value.boundaries.extension_runtime != "explicit-session-full-trust"
        || value.boundaries.remote_discovery != "unsupported"
        || value.theme_selections.len() > MAX_ITEMS
        || value.themes.len() > MAX_ITEMS
        || value.theme_packages.len() > MAX_ITEMS
        || value.extensions.len() > MAX_ITEMS
        || value.issues.len() > MAX_ISSUES
    {
        return Err(BackendCommandError::unavailable());
    }
    let mut selection_keys = BTreeSet::new();
    for item in &value.theme_selections {
        validate_qualified_id(&item.theme_id)?;
        validate_version(&item.version)?;
        validate_text(&item.theme_name, 120)?;
        if !selection_keys.insert(format!(
            "{}@{}#{}",
            item.theme_id, item.version, item.appearance
        )) {
            return Err(BackendCommandError::unavailable());
        }
        if !matches!(item.appearance.as_str(), "light" | "dark" | "high-contrast")
            || item.tokens.len() != TOKEN_NAMES.len()
            || TOKEN_NAMES.iter().any(|name| {
                item.tokens
                    .get(*name)
                    .is_none_or(|color| !valid_color(color))
            })
        {
            return Err(BackendCommandError::unavailable());
        }
    }
    for item in &value.themes {
        validate_qualified_id(&item.theme_id)?;
        validate_version(&item.version)?;
        validate_sha256(&item.package_sha256)?;
        validate_text(&item.name, 120)?;
        validate_text(&item.description, 240)?;
        validate_text(&item.source_label, 240)?;
        if item.sdk_version != 1
            || !matches!(item.state.as_str(), "active" | "disabled")
            || item.origin != "verified-external-package"
            || item.compatibility != "compatible"
            || item.trust_state != "verified-exact-package-sha256"
            || item.appearances.is_empty()
            || item.appearances.len() > 3
            || item
                .appearances
                .iter()
                .any(|value| !matches!(value.as_str(), "light" | "dark" | "high-contrast"))
        {
            return Err(BackendCommandError::unavailable());
        }
    }
    for item in &value.theme_packages {
        validate_package_filename(&item.filename)?;
        if item.valid {
            validate_qualified_id(item.theme_id.as_deref().unwrap_or_default())?;
            validate_version(item.version.as_deref().unwrap_or_default())?;
            validate_sha256(item.package_sha256.as_deref().unwrap_or_default())?;
            validate_text(item.name.as_deref().unwrap_or_default(), 120)?;
            if item.compatibility != "pending-approved-install-plan"
                || item.trust_state != "exact-hash-and-ack-required"
            {
                return Err(BackendCommandError::unavailable());
            }
        } else if item.theme_id.is_some()
            || item.name.is_some()
            || item.version.is_some()
            || item.package_sha256.is_some()
            || item.compatibility != "invalid"
            || item.trust_state != "blocked"
        {
            return Err(BackendCommandError::unavailable());
        }
    }
    for item in &value.extensions {
        validate_qualified_id(&item.plugin_id)?;
        validate_version(&item.version)?;
        validate_text(&item.name, 120)?;
        validate_text(&item.description, 240)?;
        if item.sdk_version != 1
            || item.origin != "managed-app-data"
            || item.compatibility != "compatible"
            || !matches!(
                item.trust_state.as_str(),
                "permission-request-blocked" | "full-trust-required" | "approved-for-session"
            )
            || !matches!(
                item.runtime_state.as_str(),
                "inactive" | "active" | "failed"
            )
            || item.restart_behavior != "inactive-after-restart"
            || item.capabilities.len() > 20
            || item.permissions.len() > 20
        {
            return Err(BackendCommandError::unavailable());
        }
        if let Some(digest) = &item.directory_sha256 {
            validate_sha256(digest)?;
        }
        if item
            .capabilities
            .iter()
            .chain(&item.permissions)
            .any(|metadata_id| !valid_metadata_id(metadata_id))
        {
            return Err(BackendCommandError::unavailable());
        }
        if item.permissions.is_empty() != item.directory_sha256.is_some() {
            return Err(BackendCommandError::unavailable());
        }
    }
    for issue in &value.issues {
        validate_issue(issue)?;
    }
    Ok(value)
}

fn validate_theme_result(
    value: ThemeLifecycleResult,
    expected_action: &str,
) -> Result<ThemeLifecycleResult, BackendCommandError> {
    if value.action != expected_action || value.issues.len() > MAX_ISSUES {
        return Err(BackendCommandError::unavailable());
    }
    for issue in &value.issues {
        validate_issue(issue)?;
    }
    if value.applied {
        validate_qualified_id(value.theme_id.as_deref().unwrap_or_default())?;
        validate_version(value.version.as_deref().unwrap_or_default())?;
        validate_sha256(value.package_sha256.as_deref().unwrap_or_default())?;
        if !matches!(value.state.as_deref(), Some("active" | "disabled"))
            || !value.issues.is_empty()
        {
            return Err(BackendCommandError::unavailable());
        }
    } else if value.theme_id.is_some()
        || value.version.is_some()
        || value.package_sha256.is_some()
        || value.state.is_some()
        || value.issues.is_empty()
    {
        return Err(BackendCommandError::unavailable());
    }
    Ok(value)
}

fn validate_extension_result(
    value: ExtensionRuntimeResult,
    plugin_id: &str,
    version: &str,
    digest: &str,
) -> Result<ExtensionRuntimeResult, BackendCommandError> {
    if value.plugin_id != plugin_id
        || value.version != version
        || value.directory_sha256 != digest
        || !matches!(
            value.runtime_state.as_str(),
            "active" | "inactive" | "failed"
        )
        || value.contribution_count > 100
        || value.restart_behavior != "inactive-after-restart"
        || (value.runtime_state == "failed") != value.error.is_some()
        || value
            .error
            .as_deref()
            .is_some_and(|text| text != "Extension activation failed safely.")
    {
        return Err(BackendCommandError::unavailable());
    }
    Ok(value)
}

fn validate_issue(value: &CustomizationIssue) -> Result<(), BackendCommandError> {
    if !matches!(value.area.as_str(), "theme" | "extension")
        || value.code.is_empty()
        || value.code.len() > 120
        || value.message.is_empty()
        || value.message.len() > 240
    {
        return Err(BackendCommandError::unavailable());
    }
    Ok(())
}

fn validate_extension_input(
    plugin_id: &str,
    version: &str,
    digest: &str,
    confirm: bool,
) -> Result<(), BackendCommandError> {
    validate_qualified_id(plugin_id)?;
    validate_version(version)?;
    validate_sha256(digest)?;
    validate_confirmation(confirm)
}

fn validate_qualified_id(value: &str) -> Result<(), BackendCommandError> {
    let segments: Vec<_> = value.split('.').collect();
    let valid_segment = |segment: &str| {
        segment.split('-').all(|part| {
            !part.is_empty()
                && part.as_bytes()[0].is_ascii_lowercase()
                && part
                    .bytes()
                    .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit())
        })
    };
    if value.len() > 128 || segments.len() < 2 || !segments.iter().all(|item| valid_segment(item)) {
        return Err(BackendCommandError::invalid_request(
            "The customization identity is invalid.",
        ));
    }
    Ok(())
}
fn validate_version(value: &str) -> Result<(), BackendCommandError> {
    let parts: Vec<_> = value.split('.').collect();
    if value.len() > 64
        || parts.len() != 3
        || parts.iter().any(|part| {
            part.is_empty()
                || !part.bytes().all(|byte| byte.is_ascii_digit())
                || (part.len() > 1 && part.starts_with('0'))
        })
    {
        return Err(BackendCommandError::invalid_request(
            "The customization version is invalid.",
        ));
    }
    Ok(())
}

fn valid_metadata_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value.split(['.', '-']).all(|part| {
            !part.is_empty()
                && part.as_bytes()[0].is_ascii_lowercase()
                && part
                    .bytes()
                    .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit())
        })
}

fn validate_sha256(value: &str) -> Result<(), BackendCommandError> {
    if value.len() != 64
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || matches!(byte, b'a'..=b'f'))
    {
        return Err(BackendCommandError::invalid_request(
            "The customization SHA-256 is invalid.",
        ));
    }
    Ok(())
}

fn validate_package_filename(value: &str) -> Result<(), BackendCommandError> {
    if value.is_empty()
        || value.len() > 240
        || !value.ends_with(".ups-theme.zip")
        || value.contains(['/', '\\'])
    {
        return Err(BackendCommandError::invalid_request(
            "The theme package filename is invalid.",
        ));
    }
    Ok(())
}

fn validate_confirmation(value: bool) -> Result<(), BackendCommandError> {
    if !value {
        return Err(BackendCommandError::invalid_request(
            "Customization operation requires confirmation.",
        ));
    }
    Ok(())
}

fn validate_text(value: &str, maximum: usize) -> Result<(), BackendCommandError> {
    if value.is_empty() || value.trim() != value || value.len() > maximum {
        return Err(BackendCommandError::unavailable());
    }
    Ok(())
}

fn valid_color(value: &str) -> bool {
    value.len() == 7
        && value.starts_with('#')
        && value[1..].bytes().all(|byte| byte.is_ascii_hexdigit())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn customization_inputs_are_exact_and_path_free() {
        assert!(validate_qualified_id("example.slate").is_ok());
        assert!(validate_qualified_id("../escape").is_err());
        assert!(validate_version("1.0.0").is_ok());
        assert!(validate_version("1.0").is_err());
        assert!(validate_version(&format!("{}.0.0", "1".repeat(65))).is_err());
        assert!(valid_metadata_id("network.read"));
        assert!(!valid_metadata_id("network..read"));
        assert!(validate_sha256(&"a".repeat(64)).is_ok());
        assert!(validate_package_filename("example.slate-1.0.0.ups-theme.zip").is_ok());
        assert!(validate_package_filename("../theme.ups-theme.zip").is_err());
    }

    #[test]
    fn catalog_boundary_contract_is_fixed_and_bounded() {
        let value: CustomizationCatalog = serde_json::from_str(
            r#"{
                "schema_version":1,
                "boundaries":{
                    "theme_install":"managed-inbox-only",
                    "theme_remove":"unsupported",
                    "extension_install":"unsupported",
                    "extension_remove":"unsupported",
                    "extension_runtime":"explicit-session-full-trust",
                    "remote_discovery":"unsupported"
                },
                "theme_selections":[],"themes":[],"theme_packages":[],
                "extensions":[],"issues":[]
            }"#,
        )
        .unwrap();
        assert!(validate_catalog(value).is_ok());
    }
}
