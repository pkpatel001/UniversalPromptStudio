import { invoke } from "@tauri-apps/api/core";

const REQUEST_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const QUALIFIED_ID = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:\.[a-z][a-z0-9]*(?:-[a-z0-9]+)*)+$/;
const SHA256 = /^[0-9a-f]{64}$/;
const JSON_FILENAME = /^[A-Za-z0-9._-]{1,180}\.json$/;
export const MAX_PORTABLE_DOCUMENT_CHARACTERS = 10_000;
const MAX_SUPPORT_DOCUMENT_CHARACTERS = 12_500;
const EXCLUDED = ["credentials", "execution-history", "extension-approval"];
const REDACTIONS = [
  "credentials", "prompt-content", "workflow-definitions-and-runtime-values",
  "filesystem-paths", "environment-values", "extension-code-and-contributions",
];
const SAFE_ERROR_CODES = new Set([
  "backend.unavailable", "library.invalid_input", "library.not_found", "product.unavailable",
]);

export class ProductClientError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "ProductClientError";
    this.code = code;
  }
}

export class ProductClient {
  constructor(invokeCommand = invoke, requestIdFactory = () => crypto.randomUUID()) {
    if (typeof invokeCommand !== "function" || typeof requestIdFactory !== "function") {
      throw invalidInput("Product client is invalid.");
    }
    this.invokeCommand = invokeCommand;
    this.requestIdFactory = requestIdFactory;
  }

  settings() {
    return this.#invoke("application_settings", {}, validateSettings);
  }

  saveSettings(settings, confirmed) {
    requireExactObject(settings, ["compactLayout", "onboardingCompleted", "reduceMotion"]);
    requireConfirmation(confirmed);
    return this.#invoke("application_settings_save", {
      onboardingCompleted: requireBoolean(settings.onboardingCompleted),
      compactLayout: requireBoolean(settings.compactLayout),
      reduceMotion: requireBoolean(settings.reduceMotion),
      confirm: true,
    }, validateSettings);
  }

  exportItem(kind, itemId, projectId = null) {
    validateKindAndId(kind, itemId);
    validateTarget(kind, projectId);
    return this.#invoke("portability_export", { kind, itemId, projectId }, validatePortableExport);
  }

  previewImport(document, targetProjectId = null) {
    validateDocument(document);
    validateOptionalUuid(targetProjectId);
    return this.#invoke("portability_preview", { document, targetProjectId }, validatePortablePreview);
  }

  importItem(document, targetProjectId, expectedSha256, resolution, confirmed) {
    validateDocument(document);
    validateOptionalUuid(targetProjectId);
    validateSha256(expectedSha256);
    if (!["create", "skip", "replace"].includes(resolution)) {
      throw invalidInput("Portable conflict resolution is invalid.");
    }
    requireConfirmation(confirmed);
    return this.#invoke("portability_import", {
      document, targetProjectId, expectedSha256, resolution, confirm: true,
    }, validatePortableImport);
  }

  diagnostics() {
    return this.#invoke("diagnostics_snapshot", {}, validateDiagnostics);
  }

  supportPreview() {
    return this.#invoke("support_preview", {}, validateSupportPreview);
  }

  exportSupport(expectedSha256, acknowledgeRedactionReview, confirmed) {
    validateSha256(expectedSha256);
    if (acknowledgeRedactionReview !== true) {
      throw invalidInput("Review the redaction list before exporting support data.");
    }
    requireConfirmation(confirmed);
    return this.#invoke("support_export", {
      expectedSha256, acknowledgeRedactionReview: true, confirm: true,
    }, (value) => {
      const result = validateSupportExport(value);
      if (result.documentSha256 !== expectedSha256) throw unavailable();
      return result;
    });
  }

  async #invoke(command, payload, validator) {
    const requestId = this.requestIdFactory();
    if (typeof requestId !== "string" || !REQUEST_ID.test(requestId)) {
      throw invalidInput("Product request identifier is invalid.");
    }
    try {
      return validator(await this.invokeCommand(command, { requestId, ...payload }));
    } catch (error) {
      if (error instanceof ProductClientError) throw error;
      throw normalizeError(error);
    }
  }
}

export function validateSettings(value) {
  requireExactObject(value, [
    "automaticUpdates", "compactLayout", "language", "onboardingCompleted",
    "reduceMotion", "schemaVersion", "telemetry",
  ]);
  if (
    value.schemaVersion !== 1 || value.language !== "en" ||
    value.automaticUpdates !== "unsupported" || value.telemetry !== "disabled"
  ) throw unavailable();
  requireBooleanResponse(value.onboardingCompleted);
  requireBooleanResponse(value.compactLayout);
  requireBooleanResponse(value.reduceMotion);
  return Object.freeze({ ...value });
}

export function validatePortableExport(value) {
  requireExactObject(value, [
    "document", "documentCharacters", "documentSha256", "excluded", "filename",
    "itemId", "kind", "schemaVersion", "title",
  ]);
  validateKindAndIdResponse(value.kind, value.itemId);
  validateText(value.title, 120);
  validateFilename(value.filename);
  validateDocumentResponse(value.document);
  validateSha256Response(value.documentSha256);
  if (
    value.schemaVersion !== 1 || value.documentCharacters !== [...value.document].length ||
    !exactArray(value.excluded, EXCLUDED)
  ) throw unavailable();
  return freeze(value);
}

export function validatePortablePreview(value) {
  requireExactObject(value, [
    "allowedResolutions", "changes", "conflictState", "documentCharacters",
    "documentSha256", "excluded", "itemId", "kind", "schemaVersion", "targetProjectId", "title",
  ]);
  validateKindAndIdResponse(value.kind, value.itemId);
  validateText(value.title, 120);
  validateOptionalUuidResponse(value.targetProjectId);
  validateSha256Response(value.documentSha256);
  if (
    value.schemaVersion !== 1 || !Number.isSafeInteger(value.documentCharacters) ||
    value.documentCharacters < 1 || value.documentCharacters > MAX_PORTABLE_DOCUMENT_CHARACTERS ||
    !["none", "same-target", "different-project"].includes(value.conflictState) ||
    !Array.isArray(value.allowedResolutions) || value.allowedResolutions.length < 1 ||
    value.allowedResolutions.length > 2 ||
    value.allowedResolutions.some((item) => !["create", "skip", "replace"].includes(item)) ||
    !exactArray(value.changes, [`${value.kind}-definition`]) || !exactArray(value.excluded, EXCLUDED)
  ) throw unavailable();
  return freeze(value);
}

export function validatePortableImport(value) {
  requireExactObject(value, ["applied", "itemId", "kind", "status", "targetProjectId", "title"]);
  validateKindAndIdResponse(value.kind, value.itemId);
  validateText(value.title, 120);
  validateOptionalUuidResponse(value.targetProjectId);
  requireBooleanResponse(value.applied);
  if (
    !["created", "replaced", "skipped"].includes(value.status) ||
    value.applied !== (value.status !== "skipped")
  ) throw unavailable();
  return freeze(value);
}

export function validateDiagnostics(value) {
  requireExactObject(value, [
    "application", "customizations", "library", "preferences", "providers",
    "redactions", "schemaVersion", "workflows",
  ]);
  requireExactObject(value.application, ["package", "platform", "protocolVersion", "signed", "storageSchemaVersion", "version"]);
  requireExactObject(value.library, ["projectCount", "promptCount"]);
  requireExactObject(value.workflows, ["definitionCount", "operationCount"]);
  requireExactObject(value.customizations, ["activeExtensionCount", "activeThemeCount", "extensionCount", "issueCount", "themeCount"]);
  requireExactObject(value.preferences, ["compactLayout", "onboardingCompleted", "reduceMotion"]);
  const counts = [
    ...Object.values(value.library), ...Object.values(value.workflows), ...Object.values(value.customizations),
  ];
  if (
    value.schemaVersion !== 1 || value.application.protocolVersion !== 1 ||
    value.application.storageSchemaVersion !== 1 || value.application.platform !== "windows-x64" ||
    value.application.package !== "nsis-current-user" || typeof value.application.signed !== "boolean" ||
    !counts.every((item) => Number.isSafeInteger(item) && item >= 0) ||
    value.customizations.activeThemeCount > value.customizations.themeCount ||
    value.customizations.activeExtensionCount > value.customizations.extensionCount ||
    !Array.isArray(value.providers) || value.providers.length > 20 ||
    !exactArray(value.redactions, REDACTIONS)
  ) throw unavailable();
  validateText(value.application.version, 64);
  for (const provider of value.providers) {
    requireExactObject(provider, ["available", "credentialState", "providerId"]);
    validateQualifiedIdResponse(provider.providerId);
    requireBooleanResponse(provider.available);
    validateText(provider.credentialState, 40);
  }
  for (const setting of Object.values(value.preferences)) requireBooleanResponse(setting);
  return freeze(value);
}

export function validateSupportPreview(value) {
  requireExactObject(value, [
    "containsCredentials", "containsUserContent", "documentCharacters", "documentSha256",
    "format", "includedSections", "redactions", "schemaVersion",
  ]);
  validateSha256Response(value.documentSha256);
  if (
    value.schemaVersion !== 1 || value.format !== "ups-redacted-support" ||
    value.containsCredentials !== false || value.containsUserContent !== false ||
    !Number.isSafeInteger(value.documentCharacters) || value.documentCharacters < 1 ||
    value.documentCharacters > MAX_SUPPORT_DOCUMENT_CHARACTERS ||
    !exactArray(value.includedSections, [
      "application", "library-counts", "workflow-counts", "provider-availability",
      "customization-counts", "application-preferences",
    ]) || !exactArray(value.redactions, REDACTIONS)
  ) throw unavailable();
  return freeze(value);
}

export function validateSupportExport(value) {
  requireExactObject(value, [
    "containsCredentials", "containsUserContent", "document", "documentCharacters",
    "documentSha256", "filename",
  ]);
  validateFilename(value.filename);
  validateSha256Response(value.documentSha256);
  if (
    typeof value.document !== "string" || value.document.length === 0 ||
    [...value.document].length !== value.documentCharacters ||
    value.documentCharacters > MAX_SUPPORT_DOCUMENT_CHARACTERS ||
    value.containsCredentials !== false || value.containsUserContent !== false
  ) throw unavailable();
  return freeze(value);
}

function validateTarget(kind, projectId) {
  if ((kind === "prompt" && projectId === null) || (kind === "workflow" && projectId !== null)) {
    throw invalidInput("Portable item target is invalid.");
  }
  validateOptionalUuid(projectId);
}

function validateKindAndId(kind, itemId) {
  if (kind === "prompt") validateUuid(itemId);
  else if (kind === "workflow") validateQualifiedId(itemId);
  else throw invalidInput("Portable item kind is invalid.");
}

function validateKindAndIdResponse(kind, itemId) {
  if (kind === "prompt" && typeof itemId === "string" && UUID.test(itemId)) return;
  if (kind === "workflow" && typeof itemId === "string" && QUALIFIED_ID.test(itemId)) return;
  throw unavailable();
}

function validateDocument(value) {
  if (typeof value !== "string" || value.length === 0 || [...value].length > MAX_PORTABLE_DOCUMENT_CHARACTERS) {
    throw invalidInput("Portable document is invalid or too large.");
  }
  try { JSON.parse(value); } catch { throw invalidInput("Portable document is not valid JSON."); }
  return value;
}

function validateDocumentResponse(value) {
  try { validateDocument(value); } catch { throw unavailable(); }
}

function validateUuid(value) {
  if (typeof value !== "string" || !UUID.test(value)) throw invalidInput("Portable UUID is invalid.");
  return value;
}

function validateOptionalUuid(value) {
  if (value !== null) validateUuid(value);
}

function validateOptionalUuidResponse(value) {
  if (value !== null && (typeof value !== "string" || !UUID.test(value))) throw unavailable();
}

function validateQualifiedId(value) {
  if (typeof value !== "string" || !QUALIFIED_ID.test(value)) throw invalidInput("Workflow identity is invalid.");
  return value;
}

function validateQualifiedIdResponse(value) {
  if (typeof value !== "string" || !QUALIFIED_ID.test(value)) throw unavailable();
}

function validateSha256(value) {
  if (typeof value !== "string" || !SHA256.test(value)) throw invalidInput("Reviewed SHA-256 is invalid.");
  return value;
}

function validateSha256Response(value) {
  if (typeof value !== "string" || !SHA256.test(value)) throw unavailable();
}

function validateFilename(value) {
  if (typeof value !== "string" || !JSON_FILENAME.test(value)) throw unavailable();
}

function validateText(value, maximum) {
  if (typeof value !== "string" || value.length === 0 || value.length > maximum || value.trim() !== value) throw unavailable();
}

function requireBoolean(value) {
  if (typeof value !== "boolean") throw invalidInput("Application preference is invalid.");
  return value;
}

function requireBooleanResponse(value) {
  if (typeof value !== "boolean") throw unavailable();
}

function requireConfirmation(value) {
  if (value !== true) throw invalidInput("Product operation requires confirmation.");
}

function requireExactObject(value, keys) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) throw unavailable();
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  if (actual.length !== expected.length || actual.some((item, index) => item !== expected[index])) throw unavailable();
}

function exactArray(value, expected) {
  return Array.isArray(value) && value.length === expected.length && value.every((item, index) => item === expected[index]);
}

function freeze(value) {
  return Object.freeze(structuredClone(value));
}

function normalizeError(value) {
  if (
    value !== null && typeof value === "object" && !Array.isArray(value) &&
    SAFE_ERROR_CODES.has(value.code) && typeof value.message === "string" &&
    value.message.length > 0 && value.message.length <= 256
  ) return new ProductClientError(value.code, value.message);
  return unavailable();
}

function invalidInput(message) {
  return new ProductClientError("library.invalid_input", message);
}

function unavailable() {
  return new ProductClientError("backend.unavailable", "Local product settings and support are unavailable.");
}
