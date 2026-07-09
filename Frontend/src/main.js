import "./styles.css";

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
        <button class="primary">Run Dummy Provider</button>
      </header>
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

