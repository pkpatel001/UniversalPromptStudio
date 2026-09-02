mod backend;
mod customizations;
mod workflows;

use backend::{
    BackendManager, backend_readiness, library_compose_prompt, library_create_project,
    library_create_prompt, library_delete_project, library_delete_prompt,
    library_execute_prompt_configured, library_execute_prompt_offline, library_get_prompt,
    library_projects, library_prompts, library_search_prompts, library_update_prompt,
    provider_catalog, provider_clear_credential, provider_save_settings,
};
use customizations::{
    customization_catalog, extension_activate, extension_deactivate, theme_install, theme_lifecycle,
};
use tauri::Manager;
use workflows::{
    workflow_create, workflow_delete, workflow_execute, workflow_get, workflow_operations,
    workflow_plan, workflow_update, workflows,
};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            app.manage(BackendManager::new(app.handle().clone()));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            backend_readiness,
            library_projects,
            library_create_project,
            library_delete_project,
            library_prompts,
            library_create_prompt,
            library_get_prompt,
            library_update_prompt,
            library_delete_prompt,
            library_search_prompts,
            library_compose_prompt,
            library_execute_prompt_offline,
            provider_catalog,
            provider_save_settings,
            provider_clear_credential,
            library_execute_prompt_configured,
            workflow_operations,
            workflows,
            workflow_create,
            workflow_get,
            workflow_update,
            workflow_delete,
            workflow_plan,
            workflow_execute,
            customization_catalog,
            theme_install,
            theme_lifecycle,
            extension_activate,
            extension_deactivate,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Universal Prompt Studio");
}
