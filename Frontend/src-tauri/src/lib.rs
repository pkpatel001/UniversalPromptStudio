mod backend;

use backend::{
    BackendManager, backend_readiness, library_create_project, library_create_prompt,
    library_projects, library_prompts,
};
use tauri::Manager;

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
            library_prompts,
            library_create_prompt,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Universal Prompt Studio");
}
