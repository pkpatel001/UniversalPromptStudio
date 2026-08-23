import { themeSelectionKey, THEME_CATALOG } from "./theme-catalog.js";
import { validateThemeSelection } from "./theme-controller.js";

export const THEME_PREFERENCE_STORAGE_KEY = "ups.theme.preference.v1";
const PREFERENCE_KEYS = Object.freeze([
  "appearance",
  "schemaVersion",
  "themeId",
  "version",
]);
const MAXIMUM_PREFERENCE_LENGTH = 512;

export class ThemePreferenceError extends Error {
  constructor(message) {
    super(message);
    this.name = "ThemePreferenceError";
  }
}

function requireStorage(storage) {
  if (
    storage === null ||
    typeof storage !== "object" ||
    typeof storage.getItem !== "function" ||
    typeof storage.setItem !== "function" ||
    typeof storage.removeItem !== "function"
  ) {
    throw new ThemePreferenceError("Theme preferences require a storage adapter.");
  }
}

export class ThemePreferenceStore {
  #storage;
  #catalog;

  constructor(storage, catalog = THEME_CATALOG) {
    requireStorage(storage);
    if (
      catalog === null ||
      typeof catalog !== "object" ||
      typeof catalog.selectionForIdentity !== "function" ||
      typeof catalog.selectionForKey !== "function"
    ) {
      throw new ThemePreferenceError("Theme preferences require a catalog adapter.");
    }
    this.#storage = storage;
    this.#catalog = catalog;
  }

  load() {
    let encoded;
    try {
      encoded = this.#storage.getItem(THEME_PREFERENCE_STORAGE_KEY);
    } catch {
      return Object.freeze({ status: "unavailable", selection: null });
    }
    if (encoded === null) {
      return Object.freeze({ status: "empty", selection: null });
    }
    if (typeof encoded !== "string" || encoded.length > MAXIMUM_PREFERENCE_LENGTH) {
      return Object.freeze({ status: "invalid", selection: null });
    }
    try {
      const value = JSON.parse(encoded);
      if (value === null || typeof value !== "object" || Array.isArray(value)) {
        return Object.freeze({ status: "invalid", selection: null });
      }
      const actual = Object.keys(value).sort();
      const expected = [...PREFERENCE_KEYS].sort();
      if (
        actual.length !== expected.length ||
        actual.some((item, index) => item !== expected[index]) ||
        value.schemaVersion !== 1
      ) {
        return Object.freeze({ status: "invalid", selection: null });
      }
      const selection = this.#catalog.selectionForIdentity(
        value.themeId,
        value.version,
        value.appearance,
      );
      return selection === null
        ? Object.freeze({ status: "invalid", selection: null })
        : Object.freeze({ status: "restored", selection });
    } catch {
      return Object.freeze({ status: "invalid", selection: null });
    }
  }

  save(selection) {
    const normalized = validateThemeSelection(selection);
    const known = this.#catalog.selectionForKey(themeSelectionKey(normalized));
    if (known === null) {
      throw new ThemePreferenceError("Only catalog theme selections can be remembered.");
    }
    const encoded = JSON.stringify({
      schemaVersion: 1,
      themeId: normalized.themeId,
      version: normalized.version,
      appearance: normalized.appearance,
    });
    try {
      this.#storage.setItem(THEME_PREFERENCE_STORAGE_KEY, encoded);
    } catch {
      throw new ThemePreferenceError("Theme preference could not be saved.");
    }
  }

  clear() {
    try {
      this.#storage.removeItem(THEME_PREFERENCE_STORAGE_KEY);
    } catch {
      throw new ThemePreferenceError("Theme preference could not be cleared.");
    }
  }
}
