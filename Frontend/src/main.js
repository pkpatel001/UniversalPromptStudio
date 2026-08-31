import "./styles.css";
import { BackendClient } from "./backend-client.js";
import { themeSelectionKey, THEME_CATALOG } from "./theme-catalog.js";
import { ThemeApplicationController } from "./theme-controller.js";
import { ThemePreferenceStore } from "./theme-preference.js";

document.querySelector("#app").innerHTML = `
  <main class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <p>Offline workspace</p>
        <h1>Universal Prompt Studio</h1>
      </div>
      <form id="project-form" class="compact-form">
        <label>
          New project
          <input id="project-name" name="name" maxlength="120" required
            placeholder="Project name" autocomplete="off">
        </label>
        <label>
          Description <span>optional</span>
          <textarea id="project-description" name="description" maxlength="1000"
            placeholder="What is this prompt library for?"></textarea>
        </label>
        <button class="primary" type="submit">Create project</button>
      </form>
      <div class="section-heading">
        <h2>Projects</h2>
        <span id="project-count">0</span>
      </div>
      <nav id="project-list" class="project-list" aria-label="Prompt library projects"></nav>
    </aside>

    <section class="workspace">
      <header>
        <div>
          <p>Prompt library</p>
          <h2 id="workspace-title">Choose or create a project</h2>
        </div>
        <div class="header-actions">
          <label class="theme-control">
            Theme
            <select id="theme-select">
              <option value="">Default</option>
            </select>
          </label>
          <label class="remember-theme">
            <input id="remember-theme" type="checkbox" disabled>
            Remember
          </label>
          <button id="revert-theme" class="secondary" type="button" disabled>Revert</button>
        </div>
      </header>

      <p id="theme-status" class="theme-status" role="status" aria-live="polite">
        Using the default application colors.
      </p>
      <div id="library-status" class="library-status" data-state="pending" role="status"
        aria-live="polite">
        Opening your local prompt library…
      </div>

      <section class="library-panel">
        <form id="prompt-form" class="prompt-form">
          <label>
            New prompt
            <input id="prompt-title" name="title" maxlength="120" required
              placeholder="Prompt title" autocomplete="off" disabled>
          </label>
          <button class="primary" type="submit" disabled>Create prompt</button>
        </form>

        <div class="section-heading prompt-heading">
          <div>
            <p>Saved locally</p>
            <h3>Prompts</h3>
          </div>
          <span id="prompt-count">0</span>
        </div>
        <div id="prompt-list" class="prompt-list"></div>
      </section>
    </section>
  </main>
`;

const backendClient = new BackendClient();
const projectForm = document.querySelector("#project-form");
const projectName = document.querySelector("#project-name");
const projectDescription = document.querySelector("#project-description");
const projectList = document.querySelector("#project-list");
const projectCount = document.querySelector("#project-count");
const promptForm = document.querySelector("#prompt-form");
const promptTitle = document.querySelector("#prompt-title");
const promptList = document.querySelector("#prompt-list");
const promptCount = document.querySelector("#prompt-count");
const workspaceTitle = document.querySelector("#workspace-title");
const libraryStatus = document.querySelector("#library-status");
let projects = [];
let prompts = [];
let selectedProjectId = null;

function setLibraryStatus(state, message) {
  libraryStatus.dataset.state = state;
  libraryStatus.textContent = message;
}

function selectedProject() {
  return projects.find((project) => project.projectId === selectedProjectId) ?? null;
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
  const project = selectedProject();
  workspaceTitle.textContent = project?.name ?? "Choose or create a project";
  promptTitle.disabled = project === null;
  promptForm.querySelector("button").disabled = project === null;
  if (project === null) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML = "<strong>No project selected</strong><span>Create a project to start a durable prompt library.</span>";
    promptList.append(empty);
    return;
  }
  if (prompts.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML = "<strong>No prompts yet</strong><span>Create the first prompt in this project.</span>";
    promptList.append(empty);
    return;
  }
  for (const prompt of prompts) {
    const card = document.createElement("article");
    card.className = "prompt-card";
    const marker = document.createElement("span");
    marker.className = "prompt-marker";
    marker.textContent = "P";
    const details = document.createElement("div");
    const title = document.createElement("h4");
    title.textContent = prompt.title;
    const saved = document.createElement("p");
    saved.textContent = `Saved ${new Date(prompt.createdAt).toLocaleString()}`;
    details.append(title, saved);
    card.append(marker, details);
    promptList.append(card);
  }
}

async function loadPrompts(projectId) {
  const result = await backendClient.listPrompts(projectId);
  if (selectedProjectId !== projectId) {
    return;
  }
  prompts = [...result.prompts];
  renderPrompts();
  setLibraryStatus(
    "ready",
    result.hasMore
      ? "Showing the first 50 saved prompts in this project."
      : "Your local prompt library is ready.",
  );
}

async function selectProject(projectId) {
  selectedProjectId = projectId;
  prompts = [];
  renderProjects();
  renderPrompts();
  setLibraryStatus("pending", "Loading saved prompts…");
  try {
    await loadPrompts(projectId);
  } catch (error) {
    setLibraryStatus("error", error?.message ?? "The prompt library is unavailable.");
  }
}

async function initializeLibrary(preferredProjectId = null) {
  setLibraryStatus("pending", "Opening your local prompt library…");
  try {
    await backendClient.checkReadiness();
    const result = await backendClient.listProjects();
    projects = [...result.projects];
    const preferred = projects.some((project) => project.projectId === preferredProjectId)
      ? preferredProjectId
      : projects[0]?.projectId ?? null;
    selectedProjectId = preferred;
    renderProjects();
    renderPrompts();
    if (preferred !== null) {
      await loadPrompts(preferred);
    } else {
      setLibraryStatus("ready", "Your local prompt library is ready for its first project.");
    }
  } catch (error) {
    projects = [];
    prompts = [];
    selectedProjectId = null;
    renderProjects();
    renderPrompts();
    setLibraryStatus("error", error?.message ?? "The prompt library is unavailable.");
  }
}

projectList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-project-id]");
  if (button === null || button.dataset.projectId === selectedProjectId) {
    return;
  }
  void selectProject(button.dataset.projectId);
});

projectForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = projectForm.querySelector("button");
  submit.disabled = true;
  setLibraryStatus("pending", "Creating project…");
  try {
    const result = await backendClient.createProject(
      projectName.value,
      projectDescription.value,
    );
    projectForm.reset();
    await initializeLibrary(result.project.projectId);
    projectName.focus();
  } catch (error) {
    setLibraryStatus("error", error?.message ?? "The project could not be created.");
  } finally {
    submit.disabled = false;
  }
});

promptForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (selectedProjectId === null) {
    return;
  }
  const submit = promptForm.querySelector("button");
  submit.disabled = true;
  promptTitle.disabled = true;
  setLibraryStatus("pending", "Saving prompt…");
  try {
    await backendClient.createPrompt(selectedProjectId, promptTitle.value);
    promptForm.reset();
    await loadPrompts(selectedProjectId);
    promptTitle.focus();
  } catch (error) {
    setLibraryStatus("error", error?.message ?? "The prompt could not be saved.");
  } finally {
    submit.disabled = selectedProjectId === null;
    promptTitle.disabled = selectedProjectId === null;
  }
});

const themeController = new ThemeApplicationController(document.documentElement);
const themeSelect = document.querySelector("#theme-select");
const rememberTheme = document.querySelector("#remember-theme");
const revertTheme = document.querySelector("#revert-theme");
const themeStatus = document.querySelector("#theme-status");
let preferenceStore = null;

const appearancePresentation = {
  light: { label: "Light", order: 0 },
  dark: { label: "Dark", order: 1 },
  "high-contrast": { label: "High contrast", order: 2 },
};
const presentedEntries = [...THEME_CATALOG.entries].sort(
  (left, right) =>
    appearancePresentation[left.selection.appearance].order -
    appearancePresentation[right.selection.appearance].order,
);
for (const entry of presentedEntries) {
  const option = document.createElement("option");
  option.value = entry.key;
  option.textContent =
    `${entry.themeName} — ${appearancePresentation[entry.selection.appearance].label}`;
  themeSelect.append(option);
}

try {
  preferenceStore = new ThemePreferenceStore(window.localStorage);
} catch {
  rememberTheme.disabled = true;
}

function showDefaultTheme() {
  themeSelect.value = "";
  rememberTheme.checked = false;
  rememberTheme.disabled = true;
  revertTheme.disabled = true;
  themeStatus.textContent = "Using the default application colors.";
}

function showActiveTheme(active, restored = false) {
  themeSelect.value = themeSelectionKey(active);
  rememberTheme.disabled = preferenceStore === null;
  revertTheme.disabled = false;
  themeStatus.textContent = restored
    ? `Restored ${active.appearance} theme from your saved preference.`
    : `Applied ${active.appearance} theme for this session.`;
}

if (preferenceStore !== null) {
  const preference = preferenceStore.load();
  if (preference.status === "restored") {
    try {
      showActiveTheme(themeController.apply(preference.selection), true);
      rememberTheme.checked = true;
    } catch {
      themeStatus.textContent = "Saved theme could not be applied; using default colors.";
    }
  } else if (preference.status === "invalid") {
    themeStatus.textContent = "Saved theme is invalid or unavailable; using default colors.";
  } else if (preference.status === "unavailable") {
    preferenceStore = null;
    rememberTheme.disabled = true;
    themeStatus.textContent = "Theme preferences are unavailable; using default colors.";
  }
}

themeSelect.addEventListener("change", () => {
  if (themeSelect.value === "") {
    try {
      themeController.revert();
      preferenceStore?.clear();
      showDefaultTheme();
    } catch {
      themeStatus.textContent = "Theme revert failed; the active colors were retained.";
    }
    return;
  }
  try {
    const active = themeController.apply(THEME_CATALOG.selectionForKey(themeSelect.value));
    showActiveTheme(active);
    if (rememberTheme.checked && preferenceStore !== null) {
      preferenceStore.save(active);
      themeStatus.textContent = `Applied and remembered ${active.appearance} theme.`;
    }
  } catch {
    themeStatus.textContent = "Theme change failed; the previous colors were retained.";
  }
});

rememberTheme.addEventListener("change", () => {
  try {
    const active = themeController.activeSelection;
    if (rememberTheme.checked && active !== null && preferenceStore !== null) {
      preferenceStore.save(active);
      themeStatus.textContent = `Remembering ${active.appearance} theme on this device.`;
    } else {
      preferenceStore?.clear();
      themeStatus.textContent = active
        ? `Applied ${active.appearance} theme for this session only.`
        : "Using the default application colors.";
    }
  } catch {
    rememberTheme.checked = !rememberTheme.checked;
    themeStatus.textContent = "Theme preference could not be changed.";
  }
});

revertTheme.addEventListener("click", () => {
  try {
    themeController.revert();
    preferenceStore?.clear();
    showDefaultTheme();
  } catch {
    themeStatus.textContent = "Theme revert failed; the active colors were retained.";
  }
});

renderProjects();
renderPrompts();
void initializeLibrary();
