import generatedCatalog from "./generated/theme-catalog.generated.js";
import { validateThemeSelection } from "./theme-controller.js";

const CATALOG_KEYS = Object.freeze(["schemaVersion", "selections"]);
const ENTRY_KEYS = Object.freeze([
  "appearance",
  "themeId",
  "themeName",
  "tokens",
  "version",
]);
const MAXIMUM_SELECTIONS = 1000;

export class ThemeCatalogError extends Error {
  constructor(message) {
    super(message);
    this.name = "ThemeCatalogError";
  }
}

function requireExactKeys(value, expected, label) {
  const actual = Object.keys(value).sort();
  const wanted = [...expected].sort();
  if (actual.length !== wanted.length || actual.some((item, index) => item !== wanted[index])) {
    throw new ThemeCatalogError(`${label} has an invalid shape.`);
  }
}

export function themeSelectionKey(selection) {
  const normalized = validateThemeSelection(selection);
  return `${normalized.themeId}@${normalized.version}#${normalized.appearance}`;
}

function compareStrings(left, right) {
  return left < right ? -1 : left > right ? 1 : 0;
}

function compareEntries(left, right) {
  const identity = compareStrings(left.selection.themeId, right.selection.themeId);
  if (identity !== 0) return identity;
  const leftVersion = left.selection.version.split(".").map(Number);
  const rightVersion = right.selection.version.split(".").map(Number);
  for (let index = 0; index < 3; index += 1) {
    if (leftVersion[index] !== rightVersion[index]) {
      return leftVersion[index] - rightVersion[index];
    }
  }
  return compareStrings(left.selection.appearance, right.selection.appearance);
}

export function loadThemeCatalog(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new ThemeCatalogError("Frontend theme catalog must be an object.");
  }
  requireExactKeys(value, CATALOG_KEYS, "Frontend theme catalog");
  if (value.schemaVersion !== 1) {
    throw new ThemeCatalogError("Frontend theme catalog schemaVersion must be 1.");
  }
  if (
    !Array.isArray(value.selections) ||
    value.selections.length === 0 ||
    value.selections.length > MAXIMUM_SELECTIONS
  ) {
    throw new ThemeCatalogError("Frontend theme catalog has an invalid selection count.");
  }
  const entries = [];
  const keys = new Set();
  let previousEntry = null;
  for (const valueEntry of value.selections) {
    if (valueEntry === null || typeof valueEntry !== "object" || Array.isArray(valueEntry)) {
      throw new ThemeCatalogError("Frontend theme catalog selection must be an object.");
    }
    requireExactKeys(valueEntry, ENTRY_KEYS, "Frontend theme catalog selection");
    if (
      typeof valueEntry.themeName !== "string" ||
      valueEntry.themeName.trim() !== valueEntry.themeName ||
      valueEntry.themeName.length === 0 ||
      valueEntry.themeName.length > 120
    ) {
      throw new ThemeCatalogError("Frontend theme catalog selection has an invalid name.");
    }
    const selection = validateThemeSelection({
      themeId: valueEntry.themeId,
      version: valueEntry.version,
      appearance: valueEntry.appearance,
      tokens: valueEntry.tokens,
    });
    const key = themeSelectionKey(selection);
    if (keys.has(key)) {
      throw new ThemeCatalogError("Frontend theme catalog selections must be unique.");
    }
    const entry = Object.freeze({
      key,
      themeName: valueEntry.themeName,
      selection,
    });
    if (previousEntry !== null && compareEntries(previousEntry, entry) > 0) {
      throw new ThemeCatalogError("Frontend theme catalog selections must use stable order.");
    }
    keys.add(key);
    previousEntry = entry;
    entries.push(entry);
  }
  const frozenEntries = Object.freeze(entries);
  const byKey = new Map(frozenEntries.map((entry) => [entry.key, entry.selection]));
  return Object.freeze({
    entries: frozenEntries,
    selectionForKey(key) {
      return typeof key === "string" ? (byKey.get(key) ?? null) : null;
    },
    selectionForIdentity(themeId, version, appearance) {
      if (
        typeof themeId !== "string" ||
        typeof version !== "string" ||
        typeof appearance !== "string"
      ) {
        return null;
      }
      return byKey.get(`${themeId}@${version}#${appearance}`) ?? null;
    },
  });
}

export const THEME_CATALOG = loadThemeCatalog(generatedCatalog);
