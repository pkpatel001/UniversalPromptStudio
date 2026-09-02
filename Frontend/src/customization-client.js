import { invoke } from "@tauri-apps/api/core";
import { validateThemeSelection } from "./theme-controller.js";

const REQUEST_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/;
const QUALIFIED_ID = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:\.[a-z][a-z0-9]*(?:-[a-z0-9]+)*)+$/;
const VERSION = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;
const SHA256 = /^[0-9a-f]{64}$/;
const PACKAGE_FILENAME = /^[^/\\]{1,220}\.ups-theme\.zip$/;
const MAX_ITEMS = 20;
const MAX_ISSUES = 10;
const SAFE_ERROR_CODES = new Set([
  "backend.unavailable",
  "library.invalid_input",
  "customization.blocked",
]);

export class CustomizationClientError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "CustomizationClientError";
    this.code = code;
  }
}

export class CustomizationClient {
  constructor(invokeCommand = invoke, requestIdFactory = () => crypto.randomUUID()) {
    if (typeof invokeCommand !== "function" || typeof requestIdFactory !== "function") {
      throw invalidInput("Customization client is invalid.");
    }
    this.invokeCommand = invokeCommand;
    this.requestIdFactory = requestIdFactory;
  }

  catalog() {
    return this.#invoke("customization_catalog", {}, validateCustomizationCatalog);
  }

  installTheme(themePackage, acknowledgeExternalTheme, confirmed) {
    requireExactObject(themePackage, ["filename", "packageSha256"]);
    requireConfirmation(confirmed);
    return this.#invoke(
      "theme_install",
      {
        packageFilename: validatePackageFilename(themePackage.filename),
        approvedSha256: validateSha256(themePackage.packageSha256),
        acknowledgeExternalTheme: requireBoolean(acknowledgeExternalTheme),
        confirm: true,
      },
      (value) => validateThemeLifecycleResult(value, "install"),
    );
  }

  changeThemeState(theme, action, acknowledgeLifecycleChange, confirmed) {
    requireExactObject(theme, ["packageSha256", "themeId", "version"]);
    if (!new Set(["disable", "restore"]).has(action)) {
      throw invalidInput("Theme lifecycle action is invalid.");
    }
    requireConfirmation(confirmed);
    return this.#invoke(
      "theme_lifecycle",
      {
        themeId: validateQualifiedId(theme.themeId),
        version: validateVersion(theme.version),
        action,
        approvedPackageSha256: validateSha256(theme.packageSha256),
        acknowledgeLifecycleChange: requireBoolean(acknowledgeLifecycleChange),
        confirm: true,
      },
      (value) => validateThemeLifecycleResult(value, action),
    );
  }

  activateExtension(extension, acknowledgeFullTrust, confirmed) {
    const identity = validateExtensionIdentity(extension);
    requireConfirmation(confirmed);
    return this.#invoke(
      "extension_activate",
      {
        ...identity,
        acknowledgeFullTrust: requireBoolean(acknowledgeFullTrust),
        confirm: true,
      },
      (value) => validateExtensionRuntimeResult(value, identity),
    );
  }

  deactivateExtension(extension, confirmed) {
    const identity = validateExtensionIdentity(extension);
    requireConfirmation(confirmed);
    return this.#invoke(
      "extension_deactivate",
      { ...identity, confirm: true },
      (value) => validateExtensionRuntimeResult(value, identity),
    );
  }

  async #invoke(command, payload, validator) {
    const requestId = this.requestIdFactory();
    if (typeof requestId !== "string" || !REQUEST_ID.test(requestId)) {
      throw invalidInput("Customization request identifier is invalid.");
    }
    let response;
    try {
      response = await this.invokeCommand(command, { requestId, ...payload });
    } catch (error) {
      throw normalizeError(error);
    }
    return validator(response);
  }
}

export function validateCustomizationCatalog(value) {
  requireExactObject(value, [
    "boundaries", "extensions", "issues", "schemaVersion", "themePackages",
    "themeSelections", "themes",
  ]);
  if (value.schemaVersion !== 1) throw unavailable();
  requireExactObject(value.boundaries, [
    "extensionInstall", "extensionRemove", "extensionRuntime", "remoteDiscovery",
    "themeInstall", "themeRemove",
  ]);
  if (
    value.boundaries.themeInstall !== "managed-inbox-only" ||
    value.boundaries.themeRemove !== "unsupported" ||
    value.boundaries.extensionInstall !== "unsupported" ||
    value.boundaries.extensionRemove !== "unsupported" ||
    value.boundaries.extensionRuntime !== "explicit-session-full-trust" ||
    value.boundaries.remoteDiscovery !== "unsupported"
  ) throw unavailable();
  const themeSelections = boundedArray(value.themeSelections, MAX_ITEMS).map((item) => {
    requireExactObject(item, ["appearance", "themeId", "themeName", "tokens", "version"]);
    const selection = validateThemeSelection({
      themeId: validateQualifiedId(item.themeId),
      version: validateVersion(item.version),
      appearance: item.appearance,
      tokens: item.tokens,
    });
    return Object.freeze({ ...selection, themeName: validateText(item.themeName, 120) });
  });
  const themes = boundedArray(value.themes, MAX_ITEMS).map(validateTheme);
  const themePackages = boundedArray(value.themePackages, MAX_ITEMS).map(validateThemePackage);
  const extensions = boundedArray(value.extensions, MAX_ITEMS).map(validateExtension);
  const issues = boundedArray(value.issues, MAX_ISSUES).map(validateIssue);
  return Object.freeze({
    schemaVersion: 1,
    boundaries: Object.freeze({ ...value.boundaries }),
    themeSelections: Object.freeze(themeSelections),
    themes: Object.freeze(themes),
    themePackages: Object.freeze(themePackages),
    extensions: Object.freeze(extensions),
    issues: Object.freeze(issues),
  });
}

export function validateThemeLifecycleResult(value, action) {
  requireExactObject(value, [
    "action", "applied", "issues", "packageSha256", "state", "themeId", "version",
  ]);
  if (value.action !== action || typeof value.applied !== "boolean") throw unavailable();
  const issues = boundedArray(value.issues, MAX_ISSUES).map(validateIssue);
  if (!value.applied) {
    if (
      value.themeId !== null || value.version !== null || value.packageSha256 !== null ||
      value.state !== null || issues.length === 0
    ) throw unavailable();
    return Object.freeze({ ...value, issues: Object.freeze(issues) });
  }
  if (issues.length !== 0 || !new Set(["active", "disabled"]).has(value.state)) {
    throw unavailable();
  }
  return Object.freeze({
    action,
    applied: true,
    themeId: validateQualifiedId(value.themeId),
    version: validateVersion(value.version),
    packageSha256: validateSha256(value.packageSha256),
    state: value.state,
    issues: Object.freeze([]),
  });
}

export function validateExtensionRuntimeResult(value, expected) {
  requireExactObject(value, [
    "contributionCount", "directorySha256", "error", "pluginId", "restartBehavior",
    "runtimeState", "version",
  ]);
  if (
    value.pluginId !== expected.pluginId || value.version !== expected.version ||
    value.directorySha256 !== expected.directorySha256 ||
    !new Set(["active", "inactive", "failed"]).has(value.runtimeState) ||
    !Number.isSafeInteger(value.contributionCount) || value.contributionCount < 0 ||
    value.contributionCount > 100 || value.restartBehavior !== "inactive-after-restart" ||
    (value.runtimeState === "failed" ? value.error !== "Extension activation failed safely." : value.error !== null)
  ) throw unavailable();
  return Object.freeze({ ...value });
}

function validateTheme(value) {
  requireExactObject(value, [
    "appearances", "compatibility", "description", "name", "origin", "packageSha256",
    "sdkVersion", "sourceLabel", "state", "themeId", "trustState", "version",
  ]);
  if (
    value.sdkVersion !== 1 || !new Set(["active", "disabled"]).has(value.state) ||
    value.origin !== "verified-external-package" || value.compatibility !== "compatible" ||
    value.trustState !== "verified-exact-package-sha256"
  ) throw unavailable();
  const appearances = boundedArray(value.appearances, 3);
  if (
    appearances.length === 0 || appearances.some((item) =>
      !new Set(["light", "dark", "high-contrast"]).has(item))
  ) throw unavailable();
  return Object.freeze({
    ...value,
    themeId: validateQualifiedId(value.themeId),
    version: validateVersion(value.version),
    name: validateText(value.name, 120),
    description: validateText(value.description, 240),
    packageSha256: validateSha256(value.packageSha256),
    sourceLabel: validateText(value.sourceLabel, 240),
    appearances: Object.freeze([...appearances]),
  });
}

function validateThemePackage(value) {
  requireExactObject(value, [
    "compatibility", "filename", "name", "packageSha256", "themeId", "trustState",
    "valid", "version",
  ]);
  const filename = validatePackageFilename(value.filename);
  if (typeof value.valid !== "boolean") throw unavailable();
  if (!value.valid) {
    if (
      value.themeId !== null || value.name !== null || value.version !== null ||
      value.packageSha256 !== null || value.compatibility !== "invalid" ||
      value.trustState !== "blocked"
    ) throw unavailable();
    return Object.freeze({ ...value, filename });
  }
  if (
    value.compatibility !== "pending-approved-install-plan" ||
    value.trustState !== "exact-hash-and-ack-required"
  ) throw unavailable();
  return Object.freeze({
    ...value,
    filename,
    themeId: validateQualifiedId(value.themeId),
    name: validateText(value.name, 120),
    version: validateVersion(value.version),
    packageSha256: validateSha256(value.packageSha256),
  });
}

function validateExtension(value) {
  requireExactObject(value, [
    "capabilities", "compatibility", "description", "directorySha256", "name", "origin",
    "permissions", "pluginId", "restartBehavior", "runtimeState", "sdkVersion",
    "trustState", "version",
  ]);
  if (
    value.sdkVersion !== 1 || value.origin !== "managed-app-data" ||
    value.compatibility !== "compatible" ||
    !new Set(["permission-request-blocked", "full-trust-required", "approved-for-session"]).has(value.trustState) ||
    !new Set(["inactive", "active", "failed"]).has(value.runtimeState) ||
    value.restartBehavior !== "inactive-after-restart"
  ) throw unavailable();
  const permissions = boundedArray(value.permissions, 20).map(validateMetadataId);
  const capabilities = boundedArray(value.capabilities, 20).map(validateMetadataId);
  const digest = value.directorySha256 === null ? null : validateSha256(value.directorySha256);
  if ((permissions.length === 0) !== (digest !== null)) throw unavailable();
  return Object.freeze({
    ...value,
    pluginId: validateQualifiedId(value.pluginId),
    version: validateVersion(value.version),
    name: validateText(value.name, 120),
    description: validateText(value.description, 240),
    directorySha256: digest,
    permissions: Object.freeze(permissions),
    capabilities: Object.freeze(capabilities),
  });
}

function validateIssue(value) {
  requireExactObject(value, ["area", "code", "message"]);
  if (!new Set(["theme", "extension"]).has(value.area)) throw unavailable();
  return Object.freeze({
    area: value.area,
    code: validateText(value.code, 120),
    message: validateText(value.message, 240),
  });
}

function validateExtensionIdentity(value) {
  requireExactObject(value, ["directorySha256", "pluginId", "version"]);
  return Object.freeze({
    pluginId: validateQualifiedId(value.pluginId),
    version: validateVersion(value.version),
    directorySha256: validateSha256(value.directorySha256),
  });
}

function validateQualifiedId(value) {
  if (typeof value !== "string" || value.length > 128 || !QUALIFIED_ID.test(value)) {
    throw invalidInput("Customization identity is invalid.");
  }
  return value;
}

function validateMetadataId(value) {
  if (typeof value !== "string" || value.length > 128 || !/^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$/.test(value)) throw unavailable();
  return value;
}

function validateVersion(value) {
  if (typeof value !== "string" || value.length > 64 || !VERSION.test(value)) {
    throw invalidInput("Customization version is invalid.");
  }
  return value;
}

function validateSha256(value) {
  if (typeof value !== "string" || !SHA256.test(value)) {
    throw invalidInput("Customization SHA-256 is invalid.");
  }
  return value;
}

function validatePackageFilename(value) {
  if (typeof value !== "string" || !PACKAGE_FILENAME.test(value)) {
    throw invalidInput("Theme package filename is invalid.");
  }
  return value;
}

function validateText(value, maximum) {
  if (
    typeof value !== "string" || value.length === 0 || value.length > maximum ||
    value.trim() !== value
  ) throw unavailable();
  return value;
}

function boundedArray(value, maximum) {
  if (!Array.isArray(value) || value.length > maximum) throw unavailable();
  return value;
}

function requireBoolean(value) {
  if (typeof value !== "boolean") throw invalidInput("Customization acknowledgement is invalid.");
  return value;
}

function requireConfirmation(value) {
  if (value !== true) throw invalidInput("Customization operation requires confirmation.");
}

function requireExactObject(value, keys) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) throw unavailable();
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  if (actual.length !== expected.length || actual.some((item, index) => item !== expected[index])) {
    throw unavailable();
  }
}

function normalizeError(value) {
  if (
    value !== null && typeof value === "object" && !Array.isArray(value) &&
    SAFE_ERROR_CODES.has(value.code) && typeof value.message === "string" &&
    value.message.length > 0 && value.message.length <= 256
  ) return new CustomizationClientError(value.code, value.message);
  return unavailable();
}

function invalidInput(message) {
  return new CustomizationClientError("library.invalid_input", message);
}

function unavailable() {
  return new CustomizationClientError(
    "backend.unavailable",
    "The local customization service is unavailable.",
  );
}
