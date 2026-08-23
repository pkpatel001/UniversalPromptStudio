import assert from "node:assert/strict";
import test from "node:test";

import {
  THEME_TOKEN_NAMES,
  ThemeApplicationController,
  ThemeApplicationError,
  validateThemeSelection,
} from "./theme-controller.js";
import { BUILT_IN_THEME_SELECTIONS } from "./theme-presets.js";

class FakeStyle {
  constructor() {
    this.values = new Map();
    this.failOnceOn = null;
  }

  getPropertyValue(property) {
    return this.values.get(property)?.value ?? "";
  }

  getPropertyPriority(property) {
    return this.values.get(property)?.priority ?? "";
  }

  setProperty(property, value, priority = "") {
    if (property === this.failOnceOn) {
      this.failOnceOn = null;
      throw new Error("simulated style failure");
    }
    this.values.set(property, { value, priority });
  }

  removeProperty(property) {
    const previous = this.getPropertyValue(property);
    this.values.delete(property);
    return previous;
  }
}

class FakeRoot {
  constructor() {
    this.style = new FakeStyle();
    this.attributes = new Map();
  }

  getAttribute(name) {
    return this.attributes.get(name) ?? null;
  }

  setAttribute(name, value) {
    this.attributes.set(name, value);
  }

  removeAttribute(name) {
    this.attributes.delete(name);
  }
}

function cssValue(root, name) {
  return root.style.getPropertyValue(`--ups-color-${name}`);
}

test("host-authored selections satisfy the closed E-015.4 token contract", () => {
  for (const appearance of ["light", "dark", "high-contrast"]) {
    const validated = validateThemeSelection(BUILT_IN_THEME_SELECTIONS[appearance]);
    assert.equal(validated.appearance, appearance);
    assert.deepEqual(Object.keys(validated.tokens), THEME_TOKEN_NAMES);
    assert.ok(Object.isFrozen(validated));
    assert.ok(Object.isFrozen(validated.tokens));
  }
});

test("apply writes only fixed variables and bounded selection attributes", () => {
  const root = new FakeRoot();
  const controller = new ThemeApplicationController(root);

  const active = controller.apply(BUILT_IN_THEME_SELECTIONS.dark);

  assert.equal(active, controller.activeSelection);
  assert.equal(root.style.values.size, 11);
  assert.equal(cssValue(root, "canvas"), "#101417");
  assert.equal(cssValue(root, "primary"), "#58A6B3");
  assert.equal(root.getAttribute("data-ups-theme"), "ups.built-in");
  assert.equal(root.getAttribute("data-ups-theme-version"), "1.0.0");
  assert.equal(root.getAttribute("data-ups-appearance"), "dark");
  assert.throws(() => {
    active.tokens.primary = "#000000";
  }, TypeError);
});

test("switching themes preserves the original baseline for later revert", () => {
  const root = new FakeRoot();
  root.style.setProperty("--ups-color-primary", "#112233", "important");
  root.setAttribute("data-ups-theme", "host.baseline");
  const controller = new ThemeApplicationController(root);

  controller.apply(BUILT_IN_THEME_SELECTIONS.light);
  controller.apply(BUILT_IN_THEME_SELECTIONS.dark);
  assert.equal(cssValue(root, "primary"), "#58A6B3");

  assert.equal(controller.revert(), true);
  assert.equal(controller.activeSelection, null);
  assert.equal(cssValue(root, "primary"), "#112233");
  assert.equal(root.style.getPropertyPriority("--ups-color-primary"), "important");
  assert.equal(cssValue(root, "canvas"), "");
  assert.equal(root.getAttribute("data-ups-theme"), "host.baseline");
  assert.equal(root.getAttribute("data-ups-theme-version"), null);
  assert.equal(root.getAttribute("data-ups-appearance"), null);
  assert.equal(controller.revert(), false);
});

test("failed replacement rolls every property back to the active theme", () => {
  const root = new FakeRoot();
  const controller = new ThemeApplicationController(root);
  const light = controller.apply(BUILT_IN_THEME_SELECTIONS.light);
  root.style.failOnceOn = "--ups-color-border";

  assert.throws(
    () => controller.apply(BUILT_IN_THEME_SELECTIONS.dark),
    new ThemeApplicationError("Theme application failed and was rolled back."),
  );
  assert.equal(controller.activeSelection, light);
  for (const name of THEME_TOKEN_NAMES) {
    assert.equal(cssValue(root, name), BUILT_IN_THEME_SELECTIONS.light.tokens[name]);
  }
  assert.equal(root.getAttribute("data-ups-appearance"), "light");
});

test("failed first application leaves the baseline untouched and inactive", () => {
  const root = new FakeRoot();
  root.style.setProperty("--ups-color-canvas", "#ABCDEF");
  root.style.failOnceOn = "--ups-color-border";
  const controller = new ThemeApplicationController(root);

  assert.throws(() => controller.apply(BUILT_IN_THEME_SELECTIONS.dark), ThemeApplicationError);
  assert.equal(controller.activeSelection, null);
  assert.equal(cssValue(root, "canvas"), "#ABCDEF");
  assert.equal(cssValue(root, "primary"), "");
  assert.equal(root.getAttribute("data-ups-theme"), null);
  assert.equal(controller.revert(), false);
});

test("failed revert rolls back to the complete active theme", () => {
  const root = new FakeRoot();
  root.style.setProperty("--ups-color-canvas", "#ABCDEF");
  const controller = new ThemeApplicationController(root);
  const dark = controller.apply(BUILT_IN_THEME_SELECTIONS.dark);
  root.style.failOnceOn = "--ups-color-canvas";

  assert.throws(
    () => controller.revert(),
    new ThemeApplicationError("Theme revert failed and the active theme was restored."),
  );
  assert.equal(controller.activeSelection, dark);
  for (const name of THEME_TOKEN_NAMES) {
    assert.equal(cssValue(root, name), BUILT_IN_THEME_SELECTIONS.dark.tokens[name]);
  }
  assert.equal(root.getAttribute("data-ups-appearance"), "dark");
});

test("validation rejects missing, unknown, malformed, and arbitrary values before writes", () => {
  const valid = BUILT_IN_THEME_SELECTIONS.light;
  const invalidSelections = [
    null,
    { ...valid, unknown: true },
    { ...valid, themeId: "Unqualified" },
    { ...valid, version: "1.0" },
    { ...valid, appearance: "sepia" },
    { ...valid, tokens: { ...valid.tokens, primary: "red" } },
    { ...valid, tokens: { ...valid.tokens, script: "#000000" } },
    {
      ...valid,
      tokens: Object.fromEntries(
        Object.entries(valid.tokens).filter(([name]) => name !== "focus"),
      ),
    },
  ];

  for (const selection of invalidSelections) {
    const root = new FakeRoot();
    const controller = new ThemeApplicationController(root);
    assert.throws(() => controller.apply(selection), ThemeApplicationError);
    assert.equal(root.style.values.size, 0);
    assert.equal(root.attributes.size, 0);
  }
});

test("controller rejects objects that are not DOM style roots", () => {
  assert.throws(() => new ThemeApplicationController({}), ThemeApplicationError);
  assert.throws(() => new ThemeApplicationController(null), ThemeApplicationError);
});
