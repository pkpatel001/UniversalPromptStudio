import assert from "node:assert/strict";
import test from "node:test";

import {
  CustomizationClient,
  CustomizationClientError,
  validateCustomizationCatalog,
  validateExtensionRuntimeResult,
  validateThemeLifecycleResult,
} from "./customization-client.js";

const digest = "a".repeat(64);
const tokens = {
  canvas: "#F6F8F8",
  surface: "#FFFFFF",
  "surface-muted": "#EDF3F2",
  text: "#182026",
  "text-muted": "#627277",
  border: "#DFE7E7",
  primary: "#276A73",
  "primary-text": "#FFFFFF",
  sidebar: "#12181C",
  "sidebar-text": "#F7FBFB",
  focus: "#2F7D89",
};

function emptyCatalog() {
  return {
    schemaVersion: 1,
    boundaries: {
      themeInstall: "managed-inbox-only",
      themeRemove: "unsupported",
      extensionInstall: "unsupported",
      extensionRemove: "unsupported",
      extensionRuntime: "explicit-session-full-trust",
      remoteDiscovery: "unsupported",
    },
    themeSelections: [],
    themes: [],
    themePackages: [],
    extensions: [],
    issues: [],
  };
}

test("catalog validates fixed boundaries and semantic theme tokens", () => {
  const value = emptyCatalog();
  value.themeSelections.push({
    themeId: "example.slate",
    themeName: "Slate",
    version: "1.0.0",
    appearance: "light",
    tokens,
  });
  value.themes.push({
    themeId: "example.slate",
    name: "Slate",
    version: "1.0.0",
    description: "A verified theme.",
    sdkVersion: 1,
    state: "active",
    origin: "verified-external-package",
    compatibility: "compatible",
    trustState: "verified-exact-package-sha256",
    packageSha256: digest,
    sourceLabel: "managed-inbox/example.slate-1.0.0.ups-theme.zip",
    appearances: ["light"],
  });

  const catalog = validateCustomizationCatalog(value);

  assert.equal(catalog.themeSelections[0].tokens.primary, "#276A73");
  assert.equal(catalog.themes[0].state, "active");
  assert.throws(
    () => validateCustomizationCatalog({ ...value, unexpected: true }),
    CustomizationClientError,
  );
  const unstable = emptyCatalog();
  unstable.themeSelections.push({
    themeId: "example.slate",
    themeName: "Slate",
    version: "01.0.0",
    appearance: "light",
    tokens,
  });
  assert.throws(() => validateCustomizationCatalog(unstable), CustomizationClientError);
});

test("theme and extension lifecycle results require exact identities", () => {
  const installed = validateThemeLifecycleResult({
    action: "install",
    applied: true,
    themeId: "example.slate",
    version: "1.0.0",
    packageSha256: digest,
    state: "active",
    issues: [],
  }, "install");
  const active = validateExtensionRuntimeResult({
    pluginId: "example.echo",
    version: "1.0.0",
    directorySha256: digest,
    runtimeState: "active",
    contributionCount: 1,
    error: null,
    restartBehavior: "inactive-after-restart",
  }, { pluginId: "example.echo", version: "1.0.0", directorySha256: digest });

  assert.equal(installed.state, "active");
  assert.equal(active.runtimeState, "active");
  assert.throws(
    () => validateExtensionRuntimeResult(
      { ...active, pluginId: "example.changed" },
      { pluginId: "example.echo", version: "1.0.0", directorySha256: digest },
    ),
    CustomizationClientError,
  );
});

test("client sends only fixed commands and explicit approvals", async () => {
  const calls = [];
  const client = new CustomizationClient(async (command, payload) => {
    calls.push({ command, payload });
    if (command === "customization_catalog") return emptyCatalog();
    if (command === "theme_lifecycle") {
      return {
        action: payload.action,
        applied: true,
        themeId: payload.themeId,
        version: payload.version,
        packageSha256: payload.approvedPackageSha256,
        state: "disabled",
        issues: [],
      };
    }
    throw new Error("unexpected command");
  }, () => "request-a006");

  await client.catalog();
  await client.changeThemeState(
    { themeId: "example.slate", version: "1.0.0", packageSha256: digest },
    "disable",
    true,
    true,
  );

  assert.deepEqual(calls.map((item) => item.command), [
    "customization_catalog",
    "theme_lifecycle",
  ]);
  assert.equal(calls[1].payload.confirm, true);
  assert.equal(calls[1].payload.acknowledgeLifecycleChange, true);
  assert.equal(Object.hasOwn(calls[1].payload, "path"), false);
});

test("client blocks traversal and missing confirmation before invoke", async () => {
  let invoked = false;
  const client = new CustomizationClient(async () => {
    invoked = true;
  }, () => "request-a006");

  assert.throws(
    () => client.installTheme({ filename: "../bad.ups-theme.zip", packageSha256: digest }, true, true),
    CustomizationClientError,
  );
  assert.throws(
    () => client.activateExtension(
      { pluginId: "example.echo", version: "1.0.0", directorySha256: digest },
      true,
      false,
    ),
    CustomizationClientError,
  );
  assert.throws(
    () => client.changeThemeState(
      { themeId: "example.slate", version: "1".repeat(65), packageSha256: digest },
      "disable",
      true,
      true,
    ),
    CustomizationClientError,
  );
  await Promise.resolve();
  assert.equal(invoked, false);
});
