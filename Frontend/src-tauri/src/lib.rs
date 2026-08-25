mod backend;

use backend::{BackendManager, backend_readiness};
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            app.manage(BackendManager::new(app.handle().clone()));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![backend_readiness])
        .run(tauri::generate_context!())
        .expect("error while running Universal Prompt Studio");
}
