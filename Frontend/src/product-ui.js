import "./product.css";
import { MAX_PORTABLE_DOCUMENT_CHARACTERS, ProductClient } from "./product-client.js";

export function initializeProductUI({
  trigger,
  context,
  onImportApplied = async () => {},
  productClient = new ProductClient(),
}) {
  if (!(trigger instanceof HTMLButtonElement) || typeof context !== "function") {
    throw new TypeError("Product settings UI is invalid.");
  }
  document.body.insertAdjacentHTML("beforeend", markup());
  const ui = elements();
  const state = { settings: null, importDocument: null, preview: null, support: null };

  const status = (kind, message) => {
    ui.status.dataset.state = kind;
    ui.status.textContent = message;
  };

  function applyPreferences(settings) {
    document.documentElement.classList.toggle("compact-layout", settings.compactLayout);
    document.documentElement.classList.toggle("reduce-motion", settings.reduceMotion);
    ui.compact.checked = settings.compactLayout;
    ui.motion.checked = settings.reduceMotion;
  }

  async function loadSettings() {
    try {
      state.settings = await productClient.settings();
      applyPreferences(state.settings);
      if (!state.settings.onboardingCompleted && !ui.onboarding.open) ui.onboarding.showModal();
      return state.settings;
    } catch (error) {
      status("error", error?.message ?? "Application settings are unavailable.");
      return null;
    }
  }

  function updateExportAvailability() {
    const current = context();
    ui.exportPrompt.disabled = !current?.prompt?.promptId || !current?.projectId;
    ui.exportWorkflow.disabled = !current?.workflow?.workflowId;
    ui.promptSummary.textContent = current?.prompt?.title ?? "Select a saved prompt first.";
    ui.workflowSummary.textContent = current?.workflow?.name ?? "Select a saved workflow first.";
  }

  async function exportSelection(kind) {
    const current = context();
    const item = kind === "prompt" ? current?.prompt : current?.workflow;
    const itemId = kind === "prompt" ? item?.promptId : item?.workflowId;
    const projectId = kind === "prompt" ? current?.projectId : null;
    if (!itemId) return;
    status("pending", `Preparing the selected ${kind}…`);
    try {
      const exported = await productClient.exportItem(kind, itemId, projectId);
      downloadJson(exported.filename, exported.document);
      status("ready", `${exported.title} was exported without credentials or execution history.`);
    } catch (error) {
      status("error", error?.message ?? "The item could not be exported safely.");
    }
  }

  async function readImportFile(file) {
    resetImport();
    if (!file) return;
    if (file.size > MAX_PORTABLE_DOCUMENT_CHARACTERS * 4) {
      status("error", "That file is larger than the supported portable format.");
      return;
    }
    try {
      const document = await file.text();
      if ([...document].length > MAX_PORTABLE_DOCUMENT_CHARACTERS) throw new Error("That file is too large.");
      const parsed = JSON.parse(document);
      const targetProjectId = parsed?.kind === "prompt" ? context()?.projectId ?? null : null;
      if (parsed?.kind === "prompt" && !targetProjectId) throw new Error("Open the destination project before importing a prompt.");
      state.importDocument = document;
      state.preview = await productClient.previewImport(document, targetProjectId);
      renderImportPreview();
      status("ready", "Import preview is ready. No changes have been made.");
    } catch (error) {
      resetImport();
      status("error", error?.message ?? "The portable file could not be previewed.");
    }
  }

  function renderImportPreview() {
    const preview = state.preview;
    ui.importPreview.hidden = false;
    ui.importTitle.textContent = preview.title;
    ui.importDetails.textContent = `${label(preview.kind)} · ${conflictLabel(preview.conflictState)} · ${preview.documentCharacters.toLocaleString()} characters`;
    ui.resolution.replaceChildren(...preview.allowedResolutions.map((resolution) => {
      const option = document.createElement("option");
      option.value = resolution;
      option.textContent = resolutionLabel(resolution);
      return option;
    }));
    ui.importConfirm.checked = false;
    ui.applyImport.disabled = true;
  }

  function resetImport() {
    state.importDocument = null;
    state.preview = null;
    ui.importPreview.hidden = true;
    ui.importConfirm.checked = false;
    ui.applyImport.disabled = true;
  }

  async function applyImport() {
    if (!state.preview || !state.importDocument || !ui.importConfirm.checked) return;
    status("pending", "Applying the reviewed portable item…");
    try {
      const result = await productClient.importItem(
        state.importDocument,
        state.preview.targetProjectId,
        state.preview.documentSha256,
        ui.resolution.value,
        true,
      );
      await onImportApplied(result);
      status("ready", result.applied ? `${result.title} was ${result.status}.` : `${result.title} was skipped.`);
      ui.importFile.value = "";
      resetImport();
      updateExportAvailability();
    } catch (error) {
      status("error", error?.message ?? "The reviewed import could not be applied.");
    }
  }

  async function refreshDiagnostics() {
    ui.diagnostics.replaceChildren();
    status("pending", "Collecting redacted local diagnostics…");
    try {
      const value = await productClient.diagnostics();
      const cards = [
        [value.application.version, "Application version"],
        [`${value.library.projectCount} / ${value.library.promptCount}`, "Projects / prompts"],
        [`${value.workflows.definitionCount} / ${value.workflows.operationCount}`, "Workflows / trusted operations"],
        [`${value.customizations.activeThemeCount} / ${value.customizations.activeExtensionCount}`, "Active themes / extensions"],
      ];
      for (const [count, description] of cards) ui.diagnostics.append(diagnosticCard(count, description));
      ui.packageState.textContent = `${value.application.platform} · ${value.application.package} · ${value.application.signed ? "signed" : "unsigned development package"}`;
      status("ready", "Diagnostics contain counts and states only.");
    } catch (error) {
      status("error", error?.message ?? "Diagnostics are unavailable.");
    }
  }

  async function previewSupport() {
    status("pending", "Preparing the redaction review…");
    try {
      state.support = await productClient.supportPreview();
      ui.redactions.replaceChildren(...state.support.redactions.map((item) => {
        const entry = document.createElement("li");
        entry.textContent = redactionLabel(item);
        return entry;
      }));
      ui.supportMeta.textContent = `${state.support.documentCharacters.toLocaleString()} characters · no credentials · no prompt or workflow content`;
      ui.supportReview.hidden = false;
      ui.supportConfirm.checked = false;
      ui.exportSupport.disabled = true;
      status("ready", "Review what is excluded before downloading support data.");
    } catch (error) {
      status("error", error?.message ?? "The support preview is unavailable.");
    }
  }

  async function exportSupport() {
    if (!state.support || !ui.supportConfirm.checked) return;
    status("pending", "Exporting the reviewed redacted support file…");
    try {
      const result = await productClient.exportSupport(state.support.documentSha256, true, true);
      downloadJson(result.filename, result.document);
      status("ready", "The reviewed support file was downloaded.");
    } catch (error) {
      status("error", error?.message ?? "Support data could not be exported.");
    }
  }

  async function saveSettings(onboardingCompleted = state.settings?.onboardingCompleted ?? false) {
    status("pending", "Saving application preferences…");
    try {
      state.settings = await productClient.saveSettings({
        onboardingCompleted,
        compactLayout: ui.compact.checked,
        reduceMotion: ui.motion.checked,
      }, true);
      applyPreferences(state.settings);
      status("ready", "Application preferences were saved locally.");
      return true;
    } catch (error) {
      status("error", error?.message ?? "Application preferences could not be saved.");
      return false;
    }
  }

  trigger.addEventListener("click", async () => {
    updateExportAvailability();
    ui.dialog.showModal();
    await refreshDiagnostics();
  });
  ui.close.addEventListener("click", () => ui.dialog.close());
  ui.dialog.addEventListener("click", (event) => { if (event.target === ui.dialog) ui.dialog.close(); });
  ui.saveSettings.addEventListener("click", () => void saveSettings());
  ui.exportPrompt.addEventListener("click", () => void exportSelection("prompt"));
  ui.exportWorkflow.addEventListener("click", () => void exportSelection("workflow"));
  ui.importFile.addEventListener("change", () => void readImportFile(ui.importFile.files?.[0]));
  ui.importConfirm.addEventListener("change", () => { ui.applyImport.disabled = !ui.importConfirm.checked; });
  ui.applyImport.addEventListener("click", () => void applyImport());
  ui.refreshDiagnostics.addEventListener("click", () => void refreshDiagnostics());
  ui.previewSupport.addEventListener("click", () => void previewSupport());
  ui.supportConfirm.addEventListener("change", () => { ui.exportSupport.disabled = !ui.supportConfirm.checked; });
  ui.exportSupport.addEventListener("click", () => void exportSupport());
  ui.onboardingConfirm.addEventListener("change", () => { ui.completeOnboarding.disabled = !ui.onboardingConfirm.checked; });
  ui.completeOnboarding.addEventListener("click", async () => {
    if (await saveSettings(true)) ui.onboarding.close();
  });

  void loadSettings();
  return Object.freeze({ refreshContext: updateExportAvailability, refreshSettings: loadSettings });
}

function markup() {
  return `<dialog id="product-hub" class="product-hub" aria-labelledby="product-heading"><div class="product-shell">
    <header class="product-header"><div><p>Local product controls</p><h2 id="product-heading">Settings, portable files &amp; support</h2></div><div class="product-actions"><button class="secondary" type="button" data-help-topic="settings-support">How this works</button><button id="product-close" class="secondary" type="button">Close</button></div></header>
    <p id="product-status" class="product-status" role="status" aria-live="polite"></p>
    <section class="product-section" aria-labelledby="settings-heading"><div class="product-section-heading"><div><h3 id="settings-heading">Application settings</h3><p>Small, non-secret preferences saved on this device.</p></div><button id="product-save-settings" class="primary" type="button">Save settings</button></div>
      <div class="product-grid"><div class="product-card preference-list"><label><input id="compact-layout" type="checkbox">Use a more compact workspace</label><label><input id="reduce-motion" type="checkbox">Reduce interface motion</label></div><div class="product-card"><strong>Fixed privacy policy</strong><ul class="policy-list"><li>Language: English</li><li>Telemetry: disabled</li><li>Automatic updates: not enabled</li><li>Provider credentials are never exported</li></ul></div></div></section>
    <section class="product-section" aria-labelledby="portability-heading"><div class="product-section-heading"><div><h3 id="portability-heading">Import &amp; export</h3><p>Move one prompt or workflow at a time through a reviewed JSON file.</p></div><button class="secondary" type="button" data-help-topic="portability">Import guide</button></div>
      <div class="product-grid"><article class="product-card"><strong>Export selected prompt</strong><span id="export-prompt-summary">Select a saved prompt first.</span><button id="export-prompt" class="secondary" type="button" disabled>Download prompt file</button></article><article class="product-card"><strong>Export selected workflow</strong><span id="export-workflow-summary">Select a saved workflow first.</span><button id="export-workflow" class="secondary" type="button" disabled>Download workflow file</button></article></div>
      <label class="product-file">Preview a portable file<input id="import-file" type="file" accept="application/json,.json"></label>
      <div id="import-preview" class="import-preview" hidden><div><strong id="import-title"></strong><p id="import-details"></p></div><label>Conflict action<select id="import-resolution"></select></label><label class="review-check"><input id="import-confirm" type="checkbox">I reviewed this file, destination, and conflict action.</label><button id="apply-import" class="primary" type="button" disabled>Apply reviewed import</button></div>
    </section>
    <section class="product-section" aria-labelledby="diagnostics-heading"><div class="product-section-heading"><div><h3 id="diagnostics-heading">Diagnostics &amp; support</h3><p>Counts and availability states only—never prompt content, credentials, paths, or environment values.</p></div><button id="refresh-diagnostics" class="secondary" type="button">Refresh diagnostics</button></div><div id="diagnostic-grid" class="diagnostic-grid"></div><p id="package-state"></p><div class="product-actions"><button id="preview-support" class="secondary" type="button">Review support export</button></div>
      <div id="support-review" class="support-review" hidden><strong>Always excluded</strong><ul id="redaction-list" class="redaction-list"></ul><p id="support-meta"></p><label class="review-check"><input id="support-confirm" type="checkbox">I reviewed the redactions and want to download this diagnostic snapshot.</label><button id="export-support" class="primary" type="button" disabled>Download redacted support file</button></div></section>
  </div></dialog>
  <dialog id="onboarding" class="onboarding-dialog" aria-labelledby="onboarding-heading"><div class="onboarding-shell"><div><p>Welcome to your offline workspace</p><h2 id="onboarding-heading">Build reusable prompts with clear trust boundaries</h2><p>Three things to know before you begin.</p></div><div class="onboarding-grid"><article class="onboarding-card"><span>1 · Organize</span><strong>Projects own prompts</strong><p>Create a project, add prompts, then assemble them from ordered blocks.</p></article><article class="onboarding-card"><span>2 · Control</span><strong>Runs are explicit</strong><p>Nothing runs in the background. Provider and workflow actions require your confirmation.</p></article><article class="onboarding-card"><span>3 · Move safely</span><strong>Portable files are reviewed</strong><p>Imports show conflicts first. Exports omit credentials, history, and extension approvals.</p></article></div><label class="review-check"><input id="onboarding-confirm" type="checkbox">I understand these local storage and execution boundaries.</label><div class="onboarding-actions"><span>Telemetry is disabled. Automatic updates are not enabled.</span><button id="complete-onboarding" class="primary" type="button" disabled>Start using the studio</button></div></div></dialog>`;
}

function elements() {
  const get = (id) => document.querySelector(`#${id}`);
  return {
    dialog: get("product-hub"), close: get("product-close"), status: get("product-status"),
    compact: get("compact-layout"), motion: get("reduce-motion"), saveSettings: get("product-save-settings"),
    exportPrompt: get("export-prompt"), exportWorkflow: get("export-workflow"),
    promptSummary: get("export-prompt-summary"), workflowSummary: get("export-workflow-summary"),
    importFile: get("import-file"), importPreview: get("import-preview"), importTitle: get("import-title"),
    importDetails: get("import-details"), resolution: get("import-resolution"), importConfirm: get("import-confirm"), applyImport: get("apply-import"),
    diagnostics: get("diagnostic-grid"), packageState: get("package-state"), refreshDiagnostics: get("refresh-diagnostics"),
    previewSupport: get("preview-support"), supportReview: get("support-review"), redactions: get("redaction-list"),
    supportMeta: get("support-meta"), supportConfirm: get("support-confirm"), exportSupport: get("export-support"),
    onboarding: get("onboarding"), onboardingConfirm: get("onboarding-confirm"), completeOnboarding: get("complete-onboarding"),
  };
}

function diagnosticCard(value, description) {
  const card = document.createElement("article");
  card.className = "diagnostic-card";
  const count = document.createElement("strong");
  count.textContent = String(value);
  const labelNode = document.createElement("span");
  labelNode.textContent = description;
  card.append(count, labelNode);
  return card;
}

function downloadJson(filename, documentText) {
  const url = URL.createObjectURL(new Blob([documentText], { type: "application/json;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function label(kind) { return kind === "prompt" ? "Prompt" : "Workflow"; }
function conflictLabel(value) { return ({ none: "no conflict", "same-target": "existing item found", "different-project": "identity belongs to another project" })[value]; }
function resolutionLabel(value) { return ({ create: "Create new item", replace: "Replace existing item", skip: "Keep existing item" })[value]; }
function redactionLabel(value) { return ({
  credentials: "Provider credentials", "prompt-content": "Prompt titles and content",
  "workflow-definitions-and-runtime-values": "Workflow definitions and runtime values",
  "filesystem-paths": "File and folder paths", "environment-values": "Environment values",
  "extension-code-and-contributions": "Extension code and contributions",
})[value] ?? value; }
