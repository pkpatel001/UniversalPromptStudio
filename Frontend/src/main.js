import "./styles.css";
import { ThemeApplicationController } from "./theme-controller.js";
import { BUILT_IN_THEME_SELECTIONS } from "./theme-presets.js";

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
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="high-contrast">High contrast</option>
            </select>
          </label>
          <button id="revert-theme" class="secondary" type="button" disabled>Revert theme</button>
          <button class="primary">Run Dummy Provider</button>
        </div>
      </header>
      <p id="theme-status" class="theme-status" role="status" aria-live="polite">
        Using the default application colors.
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
const revertTheme = document.querySelector("#revert-theme");
const themeStatus = document.querySelector("#theme-status");

function showDefaultTheme() {
  themeSelect.value = "";
  revertTheme.disabled = true;
  themeStatus.textContent = "Using the default application colors.";
}

themeSelect.addEventListener("change", () => {
  try {
    if (themeSelect.value === "") {
      themeController.revert();
      showDefaultTheme();
      return;
    }
    const selection = BUILT_IN_THEME_SELECTIONS[themeSelect.value];
    const active = themeController.apply(selection);
    revertTheme.disabled = false;
    themeStatus.textContent = `Applied ${active.appearance} theme for this session.`;
  } catch {
    themeSelect.value = themeController.activeSelection?.appearance ?? "";
    themeStatus.textContent = "Theme change failed; the previous colors were retained.";
  }
});

revertTheme.addEventListener("click", () => {
  try {
    themeController.revert();
    showDefaultTheme();
  } catch {
    themeStatus.textContent = "Theme revert failed; the active colors were retained.";
  }
});
