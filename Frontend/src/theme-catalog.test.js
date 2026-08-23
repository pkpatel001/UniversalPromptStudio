import assert from "node:assert/strict";
import test from "node:test";

import generatedCatalog from "./generated/theme-catalog.generated.js";
import {
  loadThemeCatalog,
  ThemeCatalogError,
  themeSelectionKey,
  THEME_CATALOG,
} from "./theme-catalog.js";

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

test("generated catalog exposes three validated identity-bound selections", () => {
  assert.equal(THEME_CATALOG.entries.length, 3);
  assert.deepEqual(
    THEME_CATALOG.entries.map((entry) => entry.selection.appearance),
    ["dark", "high-contrast", "light"],
  );
  for (const entry of THEME_CATALOG.entries) {
    assert.equal(entry.themeName, "Universal Prompt Studio");
    assert.equal(THEME_CATALOG.selectionForKey(entry.key), entry.selection);
    assert.equal(themeSelectionKey(entry.selection), entry.key);
    assert.ok(Object.isFrozen(entry));
    assert.ok(Object.isFrozen(entry.selection.tokens));
  }
});

test("catalog rejects invalid envelope, schema, count, and entry shapes", () => {
  const cases = [
    null,
    { schemaVersion: 1, selections: [], extra: true },
    { schemaVersion: 2, selections: generatedCatalog.selections },
    { schemaVersion: 1, selections: [] },
    { schemaVersion: 1, selections: [null] },
    {
      schemaVersion: 1,
      selections: [{ ...clone(generatedCatalog.selections[0]), unknown: true }],
    },
    {
      schemaVersion: 1,
      selections: [{ ...clone(generatedCatalog.selections[0]), themeName: "" }],
    },
  ];

  for (const value of cases) {
    assert.throws(() => loadThemeCatalog(value), ThemeCatalogError);
  }
});

test("catalog rejects duplicate, unstable, and malformed transported selections", () => {
  const duplicate = clone(generatedCatalog);
  duplicate.selections[1] = clone(duplicate.selections[0]);
  const unstable = clone(generatedCatalog);
  unstable.selections.reverse();
  const malformed = clone(generatedCatalog);
  malformed.selections[0].tokens.primary = "url(https://example.invalid)";

  assert.throws(() => loadThemeCatalog(duplicate), /unique/);
  assert.throws(() => loadThemeCatalog(unstable), /stable order/);
  assert.throws(() => loadThemeCatalog(malformed), /#RRGGBB/);
});

test("catalog lookups return null for unknown or untyped identities", () => {
  assert.equal(THEME_CATALOG.selectionForKey("unknown@1.0.0#light"), null);
  assert.equal(THEME_CATALOG.selectionForKey(null), null);
  assert.equal(
    THEME_CATALOG.selectionForIdentity("unknown.theme", "1.0.0", "light"),
    null,
  );
  assert.equal(THEME_CATALOG.selectionForIdentity(null, "1.0.0", "light"), null);
});
