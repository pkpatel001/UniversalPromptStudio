import assert from "node:assert/strict";
import test from "node:test";

import { THEME_CATALOG } from "./theme-catalog.js";
import {
  THEME_PREFERENCE_STORAGE_KEY,
  ThemePreferenceError,
  ThemePreferenceStore,
} from "./theme-preference.js";

class FakeStorage {
  constructor() {
    this.values = new Map();
    this.failGet = false;
    this.failSet = false;
    this.failRemove = false;
  }

  getItem(key) {
    if (this.failGet) throw new Error("unavailable");
    return this.values.get(key) ?? null;
  }

  setItem(key, value) {
    if (this.failSet) throw new Error("unavailable");
    this.values.set(key, value);
  }

  removeItem(key) {
    if (this.failRemove) throw new Error("unavailable");
    this.values.delete(key);
  }
}

const dark = THEME_CATALOG.selectionForIdentity("ups.built-in", "1.0.0", "dark");

test("preference storage is empty until an explicit save", () => {
  const storage = new FakeStorage();
  const store = new ThemePreferenceStore(storage);

  assert.deepEqual(store.load(), { status: "empty", selection: null });
  assert.equal(storage.values.size, 0);
});

test("save persists identity only and load resolves current catalog tokens", () => {
  const storage = new FakeStorage();
  const store = new ThemePreferenceStore(storage);

  store.save(dark);

  const encoded = storage.getItem(THEME_PREFERENCE_STORAGE_KEY);
  assert.deepEqual(JSON.parse(encoded), {
    schemaVersion: 1,
    themeId: "ups.built-in",
    version: "1.0.0",
    appearance: "dark",
  });
  assert.equal(encoded.includes("tokens"), false);
  assert.deepEqual(store.load(), { status: "restored", selection: dark });
});

test("clear removes the opt-in preference", () => {
  const storage = new FakeStorage();
  const store = new ThemePreferenceStore(storage);
  store.save(dark);

  store.clear();

  assert.deepEqual(store.load(), { status: "empty", selection: null });
});

test("malformed, oversized, unknown, and extra preference data is never restored", () => {
  const values = [
    "not-json",
    "x".repeat(513),
    JSON.stringify({ schemaVersion: 1 }),
    JSON.stringify({
      schemaVersion: 1,
      themeId: "unknown.theme",
      version: "1.0.0",
      appearance: "dark",
    }),
    JSON.stringify({
      schemaVersion: 1,
      themeId: "ups.built-in",
      version: "1.0.0",
      appearance: "dark",
      tokens: {},
    }),
  ];

  for (const value of values) {
    const storage = new FakeStorage();
    storage.setItem(THEME_PREFERENCE_STORAGE_KEY, value);
    assert.deepEqual(new ThemePreferenceStore(storage).load(), {
      status: "invalid",
      selection: null,
    });
  }
});

test("only current catalog selections can be remembered", () => {
  const storage = new FakeStorage();
  const store = new ThemePreferenceStore(storage);
  const unknown = { ...dark, themeId: "example.unknown" };

  assert.throws(() => store.save(unknown), /Only catalog/);
  assert.equal(storage.values.size, 0);
});

test("storage failures are bounded and never expose tokens", () => {
  const storage = new FakeStorage();
  const store = new ThemePreferenceStore(storage);
  storage.failGet = true;
  assert.deepEqual(store.load(), { status: "unavailable", selection: null });
  storage.failGet = false;
  storage.failSet = true;
  assert.throws(() => store.save(dark), ThemePreferenceError);
  storage.failSet = false;
  storage.failRemove = true;
  assert.throws(() => store.clear(), ThemePreferenceError);
});

test("preference store rejects invalid storage and catalog adapters", () => {
  assert.throws(() => new ThemePreferenceStore(null), ThemePreferenceError);
  assert.throws(() => new ThemePreferenceStore(new FakeStorage(), {}), ThemePreferenceError);
});
