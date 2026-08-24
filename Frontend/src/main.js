import "./styles.css";
import { BackendClient } from "./backend-client.js";
import { themeSelectionKey, THEME_CATALOG } from "./theme-catalog.js";
import { ThemeApplicationController } from "./theme-controller.js";
import { ThemePreferenceStore } from "./theme-preference.js";

const blocks = [
  "Role",
  "Goal",
  "Context",
  "Audience",
  "Constraints",
  "Requirements",
  "Tone",
  "Output Format",
  "Reasoning Style",
  "Examples",
  "Validation Rules",
  "Final Instructions",
];

document.querySelector("#app").innerHTML = `
  <main class="app-shell">
    <aside class="sidebar">
      <h1>Universal Prompt Studio</h1>
      <nav>
        <button class="active">Builder</button>
        <button>Templates</button>
        <button>History</button>
        <button>Settings</button>
      </nav>
    </aside>
    <section class="workspace">
      <header>
        <div>
          <p>Prompt Builder</p>
          <h2>New prompt</h2>
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
            Remember theme
          </label>
          <button id="revert-theme" class="secondary" type="button" disabled>Revert theme</button>
          <button id="backend-readiness" class="primary" type="button">Check backend</button>
        </div>
      </header>
      <p id="theme-status" class="theme-status" role="status" aria-live="polite">
        Using the default application colors.
      </p>
      <p id="backend-status" class="backend-status" data-state="idle" role="status" aria-live="polite">
        Backend connection has not been checked.
      </p>
      <div class="builder-grid">
        <section class="block-list">
          ${blocks.map((block) => `<button>${block}</button>`).join("")}
        </section>
        <section class="editor">
          <label>
            Role
            <textarea>Senior software architect</textarea>
          </label>
          <label>
            Goal
            <textarea>Design a maintainable offline prompt engineering app.</textarea>
          </label>
        </section>
        <section class="preview">
          <h3>Preview</h3>
          <pre>Role:
Senior software architect

Goal:
Design a maintainable offline prompt engineering app.</pre>
        </section>
      </div>
    </section>
  </main>
`;

const themeController = new ThemeApplicationController(document.documentElement);
const themeSelect = document.querySelector("#theme-select");
const rememberTheme = document.querySelector("#remember-theme");
const revertTheme = document.querySelector("#revert-theme");
const themeStatus = document.querySelector("#theme-status");
const backendButton = document.querySelector("#backend-readiness");
const backendStatus = document.querySelector("#backend-status");
const backendClient = new BackendClient();
let preferenceStore = null;

backendButton.addEventListener("click", async () => {
  backendButton.disabled = true;
  backendButton.textContent = "Checking backend…";
  backendStatus.dataset.state = "pending";
  backendStatus.textContent = "Starting the local application backend…";
  try {
    const readiness = await backendClient.checkReadiness();
    backendStatus.dataset.state = "ready";
    backendStatus.textContent =
      `Backend ready — Universal Prompt Studio ${readiness.applicationVersion}.`;
  } catch (error) {
    backendStatus.dataset.state = "unavailable";
    backendStatus.textContent =
      error?.message ?? "The local application backend is unavailable.";
  } finally {
    backendButton.disabled = false;
    backendButton.textContent = "Check backend";
  }
});

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
      const active = themeController.apply(preference.selection);
      rememberTheme.checked = true;
      showActiveTheme(active, true);
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
    } catch {
      themeSelect.value = themeController.activeSelection
        ? themeSelectionKey(themeController.activeSelection)
        : "";
      themeStatus.textContent = "Theme revert failed; the active colors were retained.";
      return;
    }
    let preferenceCleared = true;
    if (preferenceStore !== null) {
      try {
        preferenceStore.clear();
      } catch {
        preferenceCleared = false;
      }
    }
    showDefaultTheme();
    if (!preferenceCleared) {
      themeStatus.textContent =
        "Default colors restored, but the saved preference could not be cleared.";
    }
    return;
  }
  let active;
  try {
    const selection = THEME_CATALOG.selectionForKey(themeSelect.value);
    active = themeController.apply(selection);
  } catch {
    themeSelect.value = themeController.activeSelection
      ? themeSelectionKey(themeController.activeSelection)
      : "";
    themeStatus.textContent = "Theme change failed; the previous colors were retained.";
    return;
  }
  showActiveTheme(active);
  if (rememberTheme.checked && preferenceStore !== null) {
    try {
      preferenceStore.save(active);
      themeStatus.textContent = `Applied and remembered ${active.appearance} theme.`;
    } catch {
      rememberTheme.checked = false;
      themeStatus.textContent =
        `Applied ${active.appearance} theme, but the preference could not be saved.`;
    }
  }
});

rememberTheme.addEventListener("change", () => {
  const requested = rememberTheme.checked;
  try {
    const active = themeController.activeSelection;
    if (requested) {
      if (active === null || preferenceStore === null) {
        rememberTheme.checked = false;
        return;
      }
      preferenceStore.save(active);
      themeStatus.textContent = `Remembering ${active.appearance} theme on this device.`;
    } else if (preferenceStore !== null) {
      preferenceStore.clear();
      themeStatus.textContent = active
        ? `Applied ${active.appearance} theme for this session only.`
        : "Using the default application colors.";
    }
  } catch {
    rememberTheme.checked = !requested;
    themeStatus.textContent = "Theme preference could not be changed.";
  }
});

revertTheme.addEventListener("click", () => {
  try {
    themeController.revert();
  } catch {
    themeStatus.textContent = "Theme revert failed; the active colors were retained.";
    return;
  }
  let preferenceCleared = true;
  if (preferenceStore !== null) {
    try {
      preferenceStore.clear();
    } catch {
      preferenceCleared = false;
    }
  }
  showDefaultTheme();
  if (!preferenceCleared) {
    themeStatus.textContent =
      "Default colors restored, but the saved preference could not be cleared.";
  }
});
