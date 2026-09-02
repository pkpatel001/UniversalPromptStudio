import { CustomizationClient } from "./customization-client.js";

export function initializeCustomizationUI({ trigger, onCatalog }) {
  if (!(trigger instanceof HTMLElement) || typeof onCatalog !== "function") {
    throw new TypeError("Customization UI requires a trigger and catalog callback.");
  }
  const client = new CustomizationClient();
  const dialog = document.createElement("dialog");
  dialog.className = "customization-dialog";
  dialog.setAttribute("aria-labelledby", "customization-title");
  dialog.innerHTML = `
    <div class="customization-shell">
      <header>
        <div><p>Managed customization</p><h2 id="customization-title">Themes and extensions</h2></div>
        <button class="secondary" type="button" data-close>Close</button>
      </header>
      <div class="trust-boundary">
        <strong>Local, explicit, and reviewable</strong>
        <span>Themes are declarative color tokens. Extension code runs with full host trust only for this session after exact digest approval.</span>
      </div>
      <p class="customization-status" data-status role="status" aria-live="polite">Loading managed customization state…</p>
      <section aria-labelledby="managed-themes-title">
        <div class="customization-heading"><div><p>Verified installations</p><h3 id="managed-themes-title">Managed themes</h3></div><span data-theme-count>0</span></div>
        <div data-themes class="customization-list"></div>
      </section>
      <section aria-labelledby="theme-packages-title">
        <div class="customization-heading"><div><p>App-owned inbox</p><h3 id="theme-packages-title">Theme packages</h3></div><span data-package-count>0</span></div>
        <p class="boundary-note">Only canonical <code>.ups-theme.zip</code> files already provisioned in the managed inbox can be installed. File browsing and importing arrive in A-007.</p>
        <div data-packages class="customization-list"></div>
      </section>
      <section aria-labelledby="extensions-title">
        <div class="customization-heading"><div><p>Session lifecycle</p><h3 id="extensions-title">Managed extensions</h3></div><span data-extension-count>0</span></div>
        <p class="boundary-note">Installation, removal, updates, remote discovery, requested permissions, and automatic activation are unavailable. Active extensions return to inactive after restart.</p>
        <div data-extensions class="customization-list"></div>
      </section>
      <section data-issues-section hidden aria-labelledby="customization-issues-title">
        <div class="customization-heading"><div><p>Fail-closed validation</p><h3 id="customization-issues-title">Blocked items</h3></div><span data-issue-count>0</span></div>
        <div data-issues class="customization-list"></div>
      </section>
    </div>
  `;
  document.body.append(dialog);
  const status = dialog.querySelector("[data-status]");
  const themes = dialog.querySelector("[data-themes]");
  const packages = dialog.querySelector("[data-packages]");
  const extensions = dialog.querySelector("[data-extensions]");
  const issues = dialog.querySelector("[data-issues]");
  let catalog = null;

  function setStatus(state, message) {
    status.dataset.state = state;
    status.textContent = message;
  }

  async function refresh(message = null) {
    setStatus("pending", "Verifying managed themes, packages, and extensions…");
    try {
      catalog = await client.catalog();
      renderCatalog(catalog);
      onCatalog(catalog);
      setStatus("ready", message ?? "Managed customization state is verified and current.");
      return catalog;
    } catch (error) {
      setStatus("error", error?.message ?? "Managed customization state is unavailable.");
      return null;
    }
  }

  function renderCatalog(value) {
    dialog.querySelector("[data-theme-count]").textContent = String(value.themes.length);
    dialog.querySelector("[data-package-count]").textContent = String(value.themePackages.length);
    dialog.querySelector("[data-extension-count]").textContent = String(value.extensions.length);
    dialog.querySelector("[data-issue-count]").textContent = String(value.issues.length);
    renderThemes(value.themes);
    renderPackages(value.themePackages);
    renderExtensions(value.extensions);
    renderIssues(value.issues);
  }

  function renderThemes(items) {
    themes.replaceChildren();
    if (items.length === 0) {
      themes.append(emptyState("No managed themes installed", "Built-in themes remain available in the header selector."));
      return;
    }
    for (const theme of items) {
      const action = theme.state === "active" ? "disable" : "restore";
      const card = itemCard(theme.name, `${theme.themeId} · ${theme.version}`);
      card.append(metadataRows([
        ["State", theme.state],
        ["Origin", "Verified external package"],
        ["Compatibility", theme.compatibility],
        ["Trust", "Exact package SHA-256 verified"],
        ["Package SHA-256", theme.packageSha256],
      ]));
      const acknowledgement = acknowledgementControl(
        `I understand this will ${action} this exact verified version.`,
      );
      const button = actionButton(action === "disable" ? "Disable" : "Restore", action === "disable" ? "danger subtle" : "secondary");
      button.addEventListener("click", async () => {
        if (!acknowledgement.input.checked) return setStatus("error", "A lifecycle acknowledgement is required.");
        if (!window.confirm(`${capitalize(action)} ${theme.name} ${theme.version}?`)) return;
        button.disabled = true;
        setStatus("pending", `${capitalize(action)}ing the exact verified theme…`);
        try {
          const result = await client.changeThemeState(
            { themeId: theme.themeId, version: theme.version, packageSha256: theme.packageSha256 },
            action,
            true,
            true,
          );
          if (!result.applied) {
            setStatus("error", result.issues[0]?.message ?? "The theme change was blocked.");
            return;
          }
          await refresh(`${theme.name} is now ${result.state}.`);
        } catch (error) {
          setStatus("error", error?.message ?? "The theme change failed safely.");
        } finally {
          button.disabled = false;
        }
      });
      card.append(acknowledgement.label, actionRow(button));
      themes.append(card);
    }
  }

  function renderPackages(items) {
    packages.replaceChildren();
    if (items.length === 0) {
      packages.append(emptyState("The managed inbox is empty", "No external package bytes are available to inspect or install."));
      return;
    }
    for (const themePackage of items) {
      const card = itemCard(
        themePackage.name ?? "Blocked package",
        themePackage.valid
          ? `${themePackage.themeId} · ${themePackage.version}`
          : themePackage.filename,
      );
      card.append(metadataRows([
        ["Compatibility", themePackage.compatibility],
        ["Trust", themePackage.trustState],
        ["Package SHA-256", themePackage.packageSha256 ?? "Unavailable"],
      ]));
      if (themePackage.valid) {
        const acknowledgement = acknowledgementControl(
          "I reviewed this exact SHA-256 and acknowledge this external declarative theme.",
        );
        const button = actionButton("Install verified package", "primary");
        button.addEventListener("click", async () => {
          if (!acknowledgement.input.checked) return setStatus("error", "Exact-hash and external-theme acknowledgement is required.");
          if (!window.confirm(`Install ${themePackage.name} ${themePackage.version} from the managed inbox?`)) return;
          button.disabled = true;
          setStatus("pending", "Rechecking and installing the exact theme package…");
          try {
            const result = await client.installTheme(
              { filename: themePackage.filename, packageSha256: themePackage.packageSha256 },
              true,
              true,
            );
            if (!result.applied) {
              setStatus("error", result.issues[0]?.message ?? "Theme installation was blocked.");
              return;
            }
            await refresh(`${themePackage.name} was installed but not silently applied.`);
          } catch (error) {
            setStatus("error", error?.message ?? "Theme installation failed safely.");
          } finally {
            button.disabled = false;
          }
        });
        card.append(acknowledgement.label, actionRow(button));
      }
      packages.append(card);
    }
  }

  function renderExtensions(items) {
    extensions.replaceChildren();
    if (items.length === 0) {
      extensions.append(emptyState("No managed extensions provisioned", "Extension import and installation are intentionally unavailable in A-006."));
      return;
    }
    for (const extension of items) {
      const blocked = extension.permissions.length > 0;
      const active = extension.runtimeState === "active";
      const card = itemCard(extension.name, `${extension.pluginId} · ${extension.version}`);
      card.append(metadataRows([
        ["Runtime", extension.runtimeState],
        ["Origin", "Managed app data"],
        ["Compatibility", extension.compatibility],
        ["Trust", extension.trustState],
        ["Directory SHA-256", extension.directorySha256 ?? "Blocked before digest approval"],
        ["Restart", "Inactive after restart"],
      ]));
      if (blocked) {
        const note = document.createElement("p");
        note.className = "blocked-note";
        note.textContent = `Blocked: requested permissions cannot be enforced (${extension.permissions.join(", ")}).`;
        card.append(note);
      } else {
        const acknowledgement = acknowledgementControl(
          active
            ? "I understand this deactivates the exact in-process session."
            : "I understand this exact snapshot runs in-process with full host trust for this session.",
        );
        const button = actionButton(active ? "Deactivate" : "Activate for session", active ? "danger subtle" : "primary");
        button.addEventListener("click", async () => {
          if (!acknowledgement.input.checked) return setStatus("error", "The full-trust lifecycle acknowledgement is required.");
          if (!window.confirm(`${active ? "Deactivate" : "Activate"} ${extension.name} ${extension.version}?`)) return;
          button.disabled = true;
          setStatus("pending", `${active ? "Deactivating" : "Approving and activating"} the exact extension snapshot…`);
          try {
            const identity = {
              pluginId: extension.pluginId,
              version: extension.version,
              directorySha256: extension.directorySha256,
            };
            const result = active
              ? await client.deactivateExtension(identity, true)
              : await client.activateExtension(identity, true, true);
            await refresh(
              result.runtimeState === "failed"
                ? result.error
                : `${extension.name} is ${result.runtimeState} for this session.`,
            );
          } catch (error) {
            setStatus("error", error?.message ?? "Extension lifecycle change failed safely.");
          } finally {
            button.disabled = false;
          }
        });
        card.append(acknowledgement.label, actionRow(button));
      }
      extensions.append(card);
    }
  }

  function renderIssues(items) {
    issues.replaceChildren();
    dialog.querySelector("[data-issues-section]").hidden = items.length === 0;
    for (const issue of items) {
      const card = itemCard(issue.area === "theme" ? "Theme item blocked" : "Extension item blocked", issue.code);
      const detail = document.createElement("p");
      detail.textContent = issue.message;
      card.append(detail);
      issues.append(card);
    }
  }

  trigger.addEventListener("click", () => {
    dialog.showModal();
    void refresh();
  });
  dialog.querySelector("[data-close]").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  return Object.freeze({ refresh, dialog });
}

function itemCard(title, identity) {
  const card = document.createElement("article");
  card.className = "customization-card";
  const heading = document.createElement("div");
  heading.className = "customization-card-heading";
  const titleElement = document.createElement("strong");
  titleElement.textContent = title;
  const identityElement = document.createElement("code");
  identityElement.textContent = identity;
  heading.append(titleElement, identityElement);
  card.append(heading);
  return card;
}

function metadataRows(rows) {
  const list = document.createElement("dl");
  list.className = "customization-metadata";
  for (const [label, value] of rows) {
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = value;
    list.append(term, detail);
  }
  return list;
}

function acknowledgementControl(text) {
  const label = document.createElement("label");
  label.className = "customization-ack";
  const input = document.createElement("input");
  input.type = "checkbox";
  const span = document.createElement("span");
  span.textContent = text;
  label.append(input, span);
  return { label, input };
}

function actionButton(text, className) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = text;
  return button;
}

function actionRow(button) {
  const row = document.createElement("div");
  row.className = "customization-actions";
  row.append(button);
  return row;
}

function emptyState(title, detail) {
  const state = document.createElement("div");
  state.className = "customization-empty";
  const strong = document.createElement("strong");
  strong.textContent = title;
  const span = document.createElement("span");
  span.textContent = detail;
  state.append(strong, span);
  return state;
}

function capitalize(value) {
  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
}
