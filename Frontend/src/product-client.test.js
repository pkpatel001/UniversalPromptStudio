import assert from "node:assert/strict";
import test from "node:test";

import {
  MAX_PORTABLE_DOCUMENT_CHARACTERS,
  ProductClient,
  ProductClientError,
  validateDiagnostics,
  validatePortableExport,
  validateSettings,
  validateSupportPreview,
} from "./product-client.js";

const requestId = () => "a007-request";
const projectId = "550e8400-e29b-41d4-a716-446655440000";
const promptId = "76c7169d-9e5d-4db4-bf61-856695d2a91e";
const digest = "a".repeat(64);
const excluded = ["credentials", "execution-history", "extension-approval"];
const redactions = [
  "credentials", "prompt-content", "workflow-definitions-and-runtime-values",
  "filesystem-paths", "environment-values", "extension-code-and-contributions",
];

test("settings client sends the complete confirmed preference record", async () => {
  const calls = [];
  const value = settings();
  const client = new ProductClient(async (command, payload) => {
    calls.push([command, payload]);
    return value;
  }, requestId);

  assert.deepEqual(await client.saveSettings({
    onboardingCompleted: true, compactLayout: true, reduceMotion: false,
  }, true), value);
  assert.deepEqual(calls, [["application_settings_save", {
    requestId: "a007-request", onboardingCompleted: true, compactLayout: true,
    reduceMotion: false, confirm: true,
  }]]);
});

test("portable client previews before a digest-bound confirmed import", async () => {
  const document = JSON.stringify({ schema_version: 1 });
  const calls = [];
  const client = new ProductClient(async (command, payload) => {
    calls.push([command, payload]);
    if (command === "portability_preview") return preview(document);
    return {
      kind: "prompt", itemId: promptId, title: "Portable", targetProjectId: projectId,
      applied: true, status: "created",
    };
  }, requestId);

  const reviewed = await client.previewImport(document, projectId);
  await client.importItem(document, projectId, reviewed.documentSha256, "create", true);
  assert.deepEqual(calls.map(([command]) => command), ["portability_preview", "portability_import"]);
  assert.equal(calls[1][1].confirm, true);
  assert.equal(calls[1][1].expectedSha256, digest);
});

test("portable inputs reject unconfirmed, malformed, and oversized documents locally", async () => {
  const client = new ProductClient(async () => { throw new Error("must not invoke"); }, requestId);
  assert.throws(() => client.previewImport("not json", projectId), ProductClientError);
  assert.throws(() => client.previewImport(`"${"x".repeat(MAX_PORTABLE_DOCUMENT_CHARACTERS)}"`, projectId), ProductClientError);
  assert.throws(() => client.importItem("{}", projectId, digest, "create", false), ProductClientError);
});

test("support export must match the exact reviewed digest", async () => {
  const client = new ProductClient(async () => ({
    filename: "ups-support-bbbbbbbbbbbb.json", document: "{}",
    documentSha256: "b".repeat(64), documentCharacters: 2,
    containsCredentials: false, containsUserContent: false,
  }), requestId);
  await assert.rejects(client.exportSupport(digest, true, true), ProductClientError);
});

test("response validators reject extra fields and content-bearing diagnostic shapes", () => {
  assert.throws(() => validateSettings({ ...settings(), extra: true }), ProductClientError);
  assert.throws(() => validateDiagnostics({ ...diagnostics(), promptContent: "secret" }), ProductClientError);
  assert.throws(() => validatePortableExport({ ...portableExport(), documentCharacters: 99 }), ProductClientError);
});

test("support preview requires the fixed redaction review", () => {
  const value = {
    schemaVersion: 1, format: "ups-redacted-support",
    includedSections: [
      "application", "library-counts", "workflow-counts", "provider-availability",
      "customization-counts", "application-preferences",
    ],
    redactions, containsCredentials: false, containsUserContent: false,
    documentSha256: digest, documentCharacters: 480,
  };
  assert.equal(validateSupportPreview(value).containsUserContent, false);
  assert.throws(() => validateSupportPreview({ ...value, containsUserContent: true }), ProductClientError);
});

function settings() {
  return {
    schemaVersion: 1, onboardingCompleted: true, compactLayout: true,
    reduceMotion: false, language: "en", automaticUpdates: "unsupported", telemetry: "disabled",
  };
}

function portableExport() {
  const document = "{}";
  return {
    schemaVersion: 1, kind: "prompt", itemId: promptId, title: "Portable",
    filename: `ups-prompt-${promptId}.json`, document, documentSha256: digest,
    documentCharacters: 2, excluded,
  };
}

function preview(document) {
  return {
    schemaVersion: 1, kind: "prompt", itemId: promptId, title: "Portable",
    targetProjectId: projectId, documentSha256: digest,
    documentCharacters: [...document].length, conflictState: "none",
    allowedResolutions: ["create"], changes: ["prompt-definition"], excluded,
  };
}

function diagnostics() {
  return {
    schemaVersion: 1,
    application: {
      version: "0.2.0-alpha", protocolVersion: 1, storageSchemaVersion: 1,
      platform: "windows-x64", package: "nsis-current-user", signed: false,
    },
    library: { projectCount: 1, promptCount: 2 },
    workflows: { definitionCount: 0, operationCount: 3 },
    providers: [{ providerId: "ups.offline-echo", available: true, credentialState: "not-required" }],
    customizations: {
      themeCount: 0, activeThemeCount: 0, extensionCount: 0,
      activeExtensionCount: 0, issueCount: 0,
    },
    preferences: { onboardingCompleted: true, compactLayout: false, reduceMotion: false },
    redactions,
  };
}
