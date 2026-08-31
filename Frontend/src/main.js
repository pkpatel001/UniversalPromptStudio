import "./styles.css";
import { BackendClient } from "./backend-client.js";
import { themeSelectionKey, THEME_CATALOG } from "./theme-catalog.js";
import { ThemeApplicationController } from "./theme-controller.js";
import { ThemePreferenceStore } from "./theme-preference.js";

const BLOCK_TYPES = [
  ["role", "Role"],
  ["goal", "Goal"],
  ["context", "Context"],
  ["audience", "Audience"],
  ["constraints", "Constraints"],
  ["requirements", "Requirements"],
  ["tone", "Tone"],
  ["output_format", "Output format"],
  ["reasoning_style", "Reasoning style"],
  ["examples", "Examples"],
  ["validation_rules", "Validation rules"],
  ["final_instructions", "Final instructions"],
];

document.querySelector("#app").innerHTML = `
  <main class="app-shell">
    <aside class="sidebar">
      <div class="brand"><p>Offline workspace</p><h1>Universal Prompt Studio</h1></div>
      <form id="project-form" class="compact-form">
        <label>New project<input id="project-name" maxlength="120" required placeholder="Project name" autocomplete="off"></label>
        <label>Description <span>optional</span><textarea id="project-description" maxlength="1000" placeholder="What is this library for?"></textarea></label>
        <button class="primary" type="submit">Create project</button>
      </form>
      <div class="section-heading"><h2>Projects</h2><span id="project-count">0</span></div>
      <nav id="project-list" class="project-list" aria-label="Prompt library projects"></nav>
    </aside>

    <section class="workspace">
      <header>
        <div><p>Prompt library</p><h2 id="workspace-title">Choose or create a project</h2></div>
        <div class="header-actions">
          <button id="delete-project" class="danger subtle" type="button" disabled>Delete project</button>
          <label class="theme-control">Theme<select id="theme-select"><option value="">Default</option></select></label>
          <label class="remember-theme"><input id="remember-theme" type="checkbox" disabled>Remember</label>
          <button id="revert-theme" class="secondary" type="button" disabled>Revert</button>
        </div>
      </header>
      <p id="theme-status" class="theme-status" role="status" aria-live="polite">Using the default application colors.</p>
      <div id="library-status" class="library-status" data-state="pending" role="status" aria-live="polite">Opening your local prompt library…</div>

      <section class="library-toolbar">
        <form id="prompt-form" class="prompt-form">
          <label>New prompt<input id="prompt-title" maxlength="120" required placeholder="Prompt title" autocomplete="off" disabled></label>
          <button class="primary" type="submit" disabled>Create prompt</button>
        </form>
        <form id="search-form" class="search-form">
          <label>Search this project<input id="search-query" maxlength="120" placeholder="Title, category, tag, or block" disabled></label>
          <button class="secondary" type="submit" disabled>Search</button>
          <button id="clear-search" class="secondary" type="button" disabled>Clear</button>
        </form>
      </section>

      <section class="library-grid">
        <section class="prompt-browser">
          <div class="section-heading prompt-heading"><div><p id="prompt-mode">Saved locally</p><h3>Prompts</h3></div><span id="prompt-count">0</span></div>
          <div id="prompt-list" class="prompt-list"></div>
        </section>

        <section id="editor-panel" class="editor-panel" aria-label="Prompt editor">
          <div id="editor-empty" class="empty-state"><strong>Select a prompt</strong><span>Choose a saved prompt to edit its organization and ordered blocks.</span></div>
          <form id="editor-form" hidden>
            <div class="editor-heading"><div><p>Prompt editor</p><h3>Edit saved prompt</h3></div><button id="delete-prompt" class="danger" type="button">Delete prompt</button></div>
            <div class="editor-fields">
              <label>Title<input id="editor-title" maxlength="120" required></label>
              <label>Category <span>optional</span><input id="editor-category" maxlength="80" placeholder="e.g. Marketing"></label>
              <label class="wide">Tags <span>comma separated, up to 10</span><input id="editor-tags" placeholder="research, concise, offline"></label>
            </div>
            <div class="block-heading"><div><h4>Ordered blocks</h4><p>Blocks are assembled from top to bottom.</p></div><button id="add-block" class="secondary" type="button">Add block</button></div>
            <div id="block-list" class="block-list"></div>
            <div class="editor-actions"><span id="editor-saved"></span><button class="primary" type="submit">Save changes</button></div>
          </form>
        </section>
      </section>
    </section>
  </main>
`;

const backendClient = new BackendClient();
const byId = (id) => document.querySelector(`#${id}`);
const projectForm = byId("project-form");
const projectName = byId("project-name");
const projectDescription = byId("project-description");
const projectList = byId("project-list");
const projectCount = byId("project-count");
const promptForm = byId("prompt-form");
const promptTitle = byId("prompt-title");
const promptList = byId("prompt-list");
const promptCount = byId("prompt-count");
const promptMode = byId("prompt-mode");
const workspaceTitle = byId("workspace-title");
const libraryStatus = byId("library-status");
const searchForm = byId("search-form");
const searchQuery = byId("search-query");
const clearSearch = byId("clear-search");
const deleteProject = byId("delete-project");
const editorEmpty = byId("editor-empty");
const editorForm = byId("editor-form");
const editorTitle = byId("editor-title");
const editorCategory = byId("editor-category");
const editorTags = byId("editor-tags");
const editorSaved = byId("editor-saved");
const blockList = byId("block-list");
let projects = [];
let prompts = [];
let selectedProjectId = null;
let selectedPrompt = null;
let editorBlocks = [];
let activeQuery = "";

function setLibraryStatus(state, message) {
  libraryStatus.dataset.state = state;
  libraryStatus.textContent = message;
}

function selectedProject() {
  return projects.find((project) => project.projectId === selectedProjectId) ?? null;
}

function setProjectControls(enabled) {
  promptTitle.disabled = !enabled;
  promptForm.querySelector("button").disabled = !enabled;
  searchQuery.disabled = !enabled;
  searchForm.querySelector("button[type='submit']").disabled = !enabled;
  clearSearch.disabled = !enabled || activeQuery === "";
  deleteProject.disabled = !enabled;
}

function renderProjects() {
  projectList.replaceChildren();
  projectCount.textContent = String(projects.length);
  for (const project of projects) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = project.projectId === selectedProjectId ? "active" : "";
    button.dataset.projectId = project.projectId;
    const name = document.createElement("strong");
    name.textContent = project.name;
    const description = document.createElement("span");
    description.textContent = project.description || "No description";
    button.append(name, description);
    projectList.append(button);
  }
  if (projects.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-sidebar";
    empty.textContent = "Create your first project to begin.";
    projectList.append(empty);
  }
}

function renderPrompts() {
  promptList.replaceChildren();
  promptCount.textContent = String(prompts.length);
  promptMode.textContent = activeQuery ? `Search: “${activeQuery}”` : "Saved locally";
  const project = selectedProject();
  workspaceTitle.textContent = project?.name ?? "Choose or create a project";
  setProjectControls(project !== null);
  if (project === null || prompts.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    const heading = document.createElement("strong");
    const detail = document.createElement("span");
    heading.textContent = project === null ? "No project selected" : activeQuery ? "No matches" : "No prompts yet";
    detail.textContent = project === null ? "Create a project to start a durable prompt library." : activeQuery ? "Try another local search." : "Create the first prompt in this project.";
    empty.append(heading, detail);
    promptList.append(empty);
    return;
  }
  for (const prompt of prompts) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `prompt-card${prompt.promptId === selectedPrompt?.promptId ? " active" : ""}`;
    button.dataset.promptId = prompt.promptId;
    const title = document.createElement("strong");
    title.textContent = prompt.title;
    const metadata = document.createElement("span");
    metadata.textContent = [prompt.category, ...prompt.tags].filter(Boolean).join(" · ") || "Uncategorized";
    const saved = document.createElement("small");
    saved.textContent = `Updated ${new Date(prompt.updatedAt).toLocaleString()}`;
    button.append(title, metadata, saved);
    promptList.append(button);
  }
}

function syncEditorBlocks() {
  editorBlocks = [...blockList.querySelectorAll(".block-row")].map((row) => ({
    blockType: row.querySelector("select").value,
    content: row.querySelector("textarea").value,
    enabled: row.querySelector("input[type='checkbox']").checked,
  }));
}

function renderBlocks() {
  blockList.replaceChildren();
  if (editorBlocks.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-blocks";
    empty.textContent = "No blocks yet. Add one when this prompt needs structured content.";
    blockList.append(empty);
    return;
  }
  editorBlocks.forEach((block, index) => {
    const row = document.createElement("article");
    row.className = "block-row";
    row.dataset.index = String(index);
    const order = document.createElement("span");
    order.className = "block-order";
    order.textContent = String(index + 1);
    const fields = document.createElement("div");
    fields.className = "block-fields";
    const select = document.createElement("select");
    select.setAttribute("aria-label", `Block ${index + 1} type`);
    for (const [value, label] of BLOCK_TYPES) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      option.selected = value === block.blockType;
      select.append(option);
    }
    const content = document.createElement("textarea");
    content.maxLength = 2000;
    content.required = true;
    content.value = block.content;
    content.placeholder = "Block content";
    const enabledLabel = document.createElement("label");
    enabledLabel.className = "block-enabled";
    const enabled = document.createElement("input");
    enabled.type = "checkbox";
    enabled.checked = block.enabled;
    enabledLabel.append(enabled, document.createTextNode("Enabled"));
    fields.append(select, content, enabledLabel);
    const actions = document.createElement("div");
    actions.className = "block-actions";
    for (const [action, label, disabled] of [
      ["up", "↑", index === 0], ["down", "↓", index === editorBlocks.length - 1], ["remove", "×", false],
    ]) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = action === "remove" ? "danger subtle" : "secondary";
      button.dataset.action = action;
      button.textContent = label;
      button.disabled = disabled;
      actions.append(button);
    }
    row.append(order, fields, actions);
    blockList.append(row);
  });
}

function showEditor(prompt) {
  selectedPrompt = prompt;
  editorBlocks = prompt.blocks.map(({ blockType, content, enabled }) => ({ blockType, content, enabled }));
  editorTitle.value = prompt.title;
  editorCategory.value = prompt.category ?? "";
  editorTags.value = prompt.tags.join(", ");
  editorSaved.textContent = `Last saved ${new Date(prompt.updatedAt).toLocaleString()}`;
  editorEmpty.hidden = true;
  editorForm.hidden = false;
  renderBlocks();
  renderPrompts();
}

function closeEditor() {
  selectedPrompt = null;
  editorBlocks = [];
  editorForm.hidden = true;
  editorEmpty.hidden = false;
  renderPrompts();
}

async function loadPrompts(projectId) {
  const result = activeQuery
    ? await backendClient.searchPrompts(projectId, activeQuery)
    : await backendClient.listPrompts(projectId);
  if (selectedProjectId !== projectId) return;
  prompts = [...result.prompts];
  if (selectedPrompt && !prompts.some((prompt) => prompt.promptId === selectedPrompt.promptId)) closeEditor();
  renderPrompts();
  setLibraryStatus("ready", result.hasMore ? "Showing the first 50 matching prompts." : "Your local prompt library is ready.");
}

async function selectProject(projectId) {
  selectedProjectId = projectId;
  prompts = [];
  activeQuery = "";
  searchQuery.value = "";
  closeEditor();
  renderProjects();
  setLibraryStatus("pending", "Loading saved prompts…");
  try { await loadPrompts(projectId); } catch (error) { setLibraryStatus("error", error?.message ?? "The prompt library is unavailable."); }
}

async function initializeLibrary(preferredProjectId = null) {
  setLibraryStatus("pending", "Opening your local prompt library…");
  try {
    await backendClient.checkReadiness();
    const result = await backendClient.listProjects();
    projects = [...result.projects];
    selectedProjectId = projects.some((project) => project.projectId === preferredProjectId) ? preferredProjectId : projects[0]?.projectId ?? null;
    activeQuery = "";
    searchQuery.value = "";
    closeEditor();
    renderProjects();
    if (selectedProjectId) await loadPrompts(selectedProjectId);
    else setLibraryStatus("ready", "Your local prompt library is ready for its first project.");
  } catch (error) {
    projects = []; prompts = []; selectedProjectId = null; closeEditor(); renderProjects();
    setLibraryStatus("error", error?.message ?? "The prompt library is unavailable.");
  }
}

projectList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-project-id]");
  if (button && button.dataset.projectId !== selectedProjectId) void selectProject(button.dataset.projectId);
});

promptList.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-prompt-id]");
  if (!button || !selectedProjectId) return;
  setLibraryStatus("pending", "Opening prompt…");
  try {
    const result = await backendClient.getPrompt(selectedProjectId, button.dataset.promptId);
    showEditor(result.prompt);
    setLibraryStatus("ready", "Prompt ready to edit.");
  } catch (error) { setLibraryStatus("error", error?.message ?? "The prompt could not be opened."); }
});

projectForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = projectForm.querySelector("button"); submit.disabled = true;
  try {
    const result = await backendClient.createProject(projectName.value, projectDescription.value);
    projectForm.reset(); await initializeLibrary(result.project.projectId); projectName.focus();
  } catch (error) { setLibraryStatus("error", error?.message ?? "The project could not be created."); }
  finally { submit.disabled = false; }
});

promptForm.addEventListener("submit", async (event) => {
  event.preventDefault(); if (!selectedProjectId) return;
  const submit = promptForm.querySelector("button"); submit.disabled = true;
  try {
    const result = await backendClient.createPrompt(selectedProjectId, promptTitle.value);
    promptForm.reset(); activeQuery = ""; searchQuery.value = ""; await loadPrompts(selectedProjectId); showEditor(result.prompt); editorTitle.focus();
  } catch (error) { setLibraryStatus("error", error?.message ?? "The prompt could not be saved."); }
  finally { submit.disabled = selectedProjectId === null; }
});

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault(); if (!selectedProjectId) return;
  activeQuery = searchQuery.value.trim();
  if (!activeQuery) return;
  closeEditor(); setLibraryStatus("pending", "Searching this project…");
  try { await loadPrompts(selectedProjectId); } catch (error) { setLibraryStatus("error", error?.message ?? "Search is unavailable."); }
});

clearSearch.addEventListener("click", async () => {
  if (!selectedProjectId) return;
  activeQuery = ""; searchQuery.value = ""; closeEditor(); setLibraryStatus("pending", "Loading saved prompts…");
  try { await loadPrompts(selectedProjectId); } catch (error) { setLibraryStatus("error", error?.message ?? "The prompt library is unavailable."); }
});

deleteProject.addEventListener("click", async () => {
  const project = selectedProject();
  if (!project || !window.confirm(`Delete “${project.name}” and every prompt inside it? This cannot be undone.`)) return;
  setLibraryStatus("pending", "Deleting project and dependent prompts…");
  try { await backendClient.deleteProject(project.projectId, true); await initializeLibrary(); }
  catch (error) { setLibraryStatus("error", error?.message ?? "The project could not be deleted."); }
});

byId("add-block").addEventListener("click", () => {
  if (editorBlocks.length >= 12) { setLibraryStatus("error", "A prompt supports at most 12 blocks."); return; }
  syncEditorBlocks(); editorBlocks.push({ blockType: "context", content: "", enabled: true }); renderBlocks();
  blockList.lastElementChild?.querySelector("textarea")?.focus();
});

blockList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  syncEditorBlocks();
  const index = Number(button.closest(".block-row").dataset.index);
  if (button.dataset.action === "remove") editorBlocks.splice(index, 1);
  if (button.dataset.action === "up" && index > 0) [editorBlocks[index - 1], editorBlocks[index]] = [editorBlocks[index], editorBlocks[index - 1]];
  if (button.dataset.action === "down" && index < editorBlocks.length - 1) [editorBlocks[index + 1], editorBlocks[index]] = [editorBlocks[index], editorBlocks[index + 1]];
  renderBlocks();
});

editorForm.addEventListener("submit", async (event) => {
  event.preventDefault(); if (!selectedProjectId || !selectedPrompt) return;
  syncEditorBlocks();
  const tags = editorTags.value.split(",").map((tag) => tag.trim()).filter(Boolean);
  const submit = editorForm.querySelector("button[type='submit']"); submit.disabled = true;
  setLibraryStatus("pending", "Saving prompt changes…");
  try {
    const result = await backendClient.updatePrompt(selectedProjectId, selectedPrompt.promptId, {
      title: editorTitle.value, category: editorCategory.value || null, tags, blocks: editorBlocks,
    });
    showEditor(result.prompt); await loadPrompts(selectedProjectId); setLibraryStatus("ready", "Prompt changes saved locally.");
  } catch (error) { setLibraryStatus("error", error?.message ?? "The prompt could not be updated."); }
  finally { submit.disabled = false; }
});

byId("delete-prompt").addEventListener("click", async () => {
  if (!selectedProjectId || !selectedPrompt || !window.confirm(`Delete “${selectedPrompt.title}”? This cannot be undone.`)) return;
  setLibraryStatus("pending", "Deleting prompt…");
  try { await backendClient.deletePrompt(selectedProjectId, selectedPrompt.promptId, true); closeEditor(); await loadPrompts(selectedProjectId); }
  catch (error) { setLibraryStatus("error", error?.message ?? "The prompt could not be deleted."); }
});

const themeController = new ThemeApplicationController(document.documentElement);
const themeSelect = byId("theme-select");
const rememberTheme = byId("remember-theme");
const revertTheme = byId("revert-theme");
const themeStatus = byId("theme-status");
let preferenceStore = null;
const appearancePresentation = { light: { label: "Light", order: 0 }, dark: { label: "Dark", order: 1 }, "high-contrast": { label: "High contrast", order: 2 } };
for (const entry of [...THEME_CATALOG.entries].sort((a, b) => appearancePresentation[a.selection.appearance].order - appearancePresentation[b.selection.appearance].order)) {
  const option = document.createElement("option"); option.value = entry.key; option.textContent = `${entry.themeName} — ${appearancePresentation[entry.selection.appearance].label}`; themeSelect.append(option);
}
try { preferenceStore = new ThemePreferenceStore(window.localStorage); } catch { rememberTheme.disabled = true; }
function showDefaultTheme() { themeSelect.value = ""; rememberTheme.checked = false; rememberTheme.disabled = true; revertTheme.disabled = true; themeStatus.textContent = "Using the default application colors."; }
function showActiveTheme(active, restored = false) { themeSelect.value = themeSelectionKey(active); rememberTheme.disabled = preferenceStore === null; revertTheme.disabled = false; themeStatus.textContent = restored ? `Restored ${active.appearance} theme from your saved preference.` : `Applied ${active.appearance} theme for this session.`; }
if (preferenceStore) {
  const preference = preferenceStore.load();
  if (preference.status === "restored") { try { showActiveTheme(themeController.apply(preference.selection), true); rememberTheme.checked = true; } catch { themeStatus.textContent = "Saved theme could not be applied; using default colors."; } }
  else if (preference.status === "invalid") themeStatus.textContent = "Saved theme is invalid or unavailable; using default colors.";
  else if (preference.status === "unavailable") { preferenceStore = null; rememberTheme.disabled = true; themeStatus.textContent = "Theme preferences are unavailable; using default colors."; }
}
themeSelect.addEventListener("change", () => {
  if (!themeSelect.value) { try { themeController.revert(); preferenceStore?.clear(); showDefaultTheme(); } catch { themeStatus.textContent = "Theme revert failed; the active colors were retained."; } return; }
  try { const active = themeController.apply(THEME_CATALOG.selectionForKey(themeSelect.value)); showActiveTheme(active); if (rememberTheme.checked && preferenceStore) { preferenceStore.save(active); themeStatus.textContent = `Applied and remembered ${active.appearance} theme.`; } } catch { themeStatus.textContent = "Theme change failed; the previous colors were retained."; }
});
rememberTheme.addEventListener("change", () => { try { const active = themeController.activeSelection; if (rememberTheme.checked && active && preferenceStore) { preferenceStore.save(active); themeStatus.textContent = `Remembering ${active.appearance} theme on this device.`; } else { preferenceStore?.clear(); themeStatus.textContent = active ? `Applied ${active.appearance} theme for this session only.` : "Using the default application colors."; } } catch { rememberTheme.checked = !rememberTheme.checked; themeStatus.textContent = "Theme preference could not be changed."; } });
revertTheme.addEventListener("click", () => { try { themeController.revert(); preferenceStore?.clear(); showDefaultTheme(); } catch { themeStatus.textContent = "Theme revert failed; the active colors were retained."; } });

renderProjects(); renderPrompts(); void initializeLibrary();
