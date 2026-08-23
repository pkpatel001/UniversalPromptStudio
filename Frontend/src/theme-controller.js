export const THEME_TOKEN_NAMES = Object.freeze([
  "canvas",
  "surface",
  "surface-muted",
  "text",
  "text-muted",
  "border",
  "primary",
  "primary-text",
  "sidebar",
  "sidebar-text",
  "focus",
]);

const SELECTION_KEYS = Object.freeze(["appearance", "themeId", "tokens", "version"]);
const APPEARANCES = new Set(["light", "dark", "high-contrast"]);
const THEME_ID = /^[a-z0-9]+(?:[.-][a-z0-9]+)+$/;
const THEME_VERSION = /^\d+\.\d+\.\d+$/;
const COLOR = /^#[0-9A-Fa-f]{6}$/;

const ATTRIBUTES = Object.freeze({
  themeId: "data-ups-theme",
  version: "data-ups-theme-version",
  appearance: "data-ups-appearance",
});

export class ThemeApplicationError extends Error {
  constructor(message) {
    super(message);
    this.name = "ThemeApplicationError";
  }
}

function requireExactKeys(value, expected, label) {
  const actual = Object.keys(value).sort();
  const wanted = [...expected].sort();
  if (actual.length !== wanted.length || actual.some((item, index) => item !== wanted[index])) {
    throw new ThemeApplicationError(`${label} must contain exactly: ${wanted.join(", ")}.`);
  }
}

export function validateThemeSelection(selection) {
  if (selection === null || typeof selection !== "object" || Array.isArray(selection)) {
    throw new ThemeApplicationError("Theme selection must be an object.");
  }
  requireExactKeys(selection, SELECTION_KEYS, "Theme selection");
  if (typeof selection.themeId !== "string" || !THEME_ID.test(selection.themeId)) {
    throw new ThemeApplicationError("Theme selection requires a vendor-qualified themeId.");
  }
  if (typeof selection.version !== "string" || !THEME_VERSION.test(selection.version)) {
    throw new ThemeApplicationError("Theme selection requires a major.minor.patch version.");
  }
  if (typeof selection.appearance !== "string" || !APPEARANCES.has(selection.appearance)) {
    throw new ThemeApplicationError("Theme selection has an unsupported appearance.");
  }
  if (selection.tokens === null || typeof selection.tokens !== "object" || Array.isArray(selection.tokens)) {
    throw new ThemeApplicationError("Theme selection tokens must be an object.");
  }
  requireExactKeys(selection.tokens, THEME_TOKEN_NAMES, "Theme selection tokens");
  const tokens = {};
  for (const name of THEME_TOKEN_NAMES) {
    const value = selection.tokens[name];
    if (typeof value !== "string" || !COLOR.test(value)) {
      throw new ThemeApplicationError(`Theme token ${name} must be an opaque #RRGGBB color.`);
    }
    tokens[name] = value;
  }
  return Object.freeze({
    themeId: selection.themeId,
    version: selection.version,
    appearance: selection.appearance,
    tokens: Object.freeze(tokens),
  });
}

function requireThemeRoot(root) {
  if (
    root === null ||
    typeof root !== "object" ||
    root.style === null ||
    typeof root.style !== "object" ||
    typeof root.style.getPropertyValue !== "function" ||
    typeof root.style.getPropertyPriority !== "function" ||
    typeof root.style.setProperty !== "function" ||
    typeof root.style.removeProperty !== "function" ||
    typeof root.getAttribute !== "function" ||
    typeof root.setAttribute !== "function" ||
    typeof root.removeAttribute !== "function"
  ) {
    throw new ThemeApplicationError("Theme application requires a DOM style root.");
  }
}

export class ThemeApplicationController {
  #root;
  #baseline = null;
  #activeSelection = null;

  constructor(root) {
    requireThemeRoot(root);
    this.#root = root;
  }

  get activeSelection() {
    return this.#activeSelection;
  }

  apply(selection) {
    const normalized = validateThemeSelection(selection);
    const previous = this.#snapshot();
    const firstApplication = this.#baseline === null;
    try {
      for (const name of THEME_TOKEN_NAMES) {
        this.#root.style.setProperty(`--ups-color-${name}`, normalized.tokens[name]);
      }
      this.#root.setAttribute(ATTRIBUTES.themeId, normalized.themeId);
      this.#root.setAttribute(ATTRIBUTES.version, normalized.version);
      this.#root.setAttribute(ATTRIBUTES.appearance, normalized.appearance);
    } catch {
      try {
        this.#restore(previous);
      } catch {
        throw new ThemeApplicationError("Theme application failed and rollback was incomplete.");
      }
      throw new ThemeApplicationError("Theme application failed and was rolled back.");
    }
    if (firstApplication) {
      this.#baseline = previous;
    }
    this.#activeSelection = normalized;
    return normalized;
  }

  revert() {
    if (this.#baseline === null) {
      return false;
    }
    const active = this.#snapshot();
    try {
      this.#restore(this.#baseline);
    } catch {
      try {
        this.#restore(active);
      } catch {
        throw new ThemeApplicationError("Theme revert failed and rollback was incomplete.");
      }
      throw new ThemeApplicationError("Theme revert failed and the active theme was restored.");
    }
    this.#baseline = null;
    this.#activeSelection = null;
    return true;
  }

  #snapshot() {
    return {
      properties: THEME_TOKEN_NAMES.map((name) => {
        const property = `--ups-color-${name}`;
        return {
          property,
          value: this.#root.style.getPropertyValue(property),
          priority: this.#root.style.getPropertyPriority(property),
        };
      }),
      attributes: Object.values(ATTRIBUTES).map((name) => ({
        name,
        value: this.#root.getAttribute(name),
      })),
    };
  }

  #restore(snapshot) {
    for (const item of snapshot.properties) {
      if (item.value === "") {
        this.#root.style.removeProperty(item.property);
      } else {
        this.#root.style.setProperty(item.property, item.value, item.priority);
      }
    }
    for (const item of snapshot.attributes) {
      if (item.value === null) {
        this.#root.removeAttribute(item.name);
      } else {
        this.#root.setAttribute(item.name, item.value);
      }
    }
  }
}
