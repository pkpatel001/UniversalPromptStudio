mod backend;

use backend::{BackendManager, backend_readiness};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(BackendManager::new())
        .invoke_handler(tauri::generate_handler![backend_readiness])
        .run(tauri::generate_context!())
        .expect("error while running Universal Prompt Studio");
}
