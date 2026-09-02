import { invoke } from "@tauri-apps/api/core";

const REQUEST_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/;
const IDENTIFIER = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const VERSION = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/;
const TIMESTAMP = /^\d{4}-\d{2}-\d{2}T[^\s]{8,28}Z$/;
const BLOCK_TYPES = new Set([
  "role", "goal", "context", "audience", "constraints", "requirements", "tone",
  "output_format", "reasoning_style", "examples", "validation_rules", "final_instructions",
]);

export const OFFLINE_REFERENCE_PROVIDER = "ups.offline-echo";
export const OPENAI_RESPONSES_PROVIDER = "ups.openai-responses";
export const OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses";
const OPENAI_CREDENTIAL_REFERENCE = "provider:ups.openai-responses:default";
const CAPABILITIES = Object.freeze([
  "application.readiness",
  "library.projects.list",
  "library.projects.create",
  "library.projects.delete",
  "library.prompts.list",
  "library.prompts.create",
  "library.prompts.get",
  "library.prompts.update",
  "library.prompts.delete",
  "library.prompts.search",
  "library.prompts.compose",
  "library.prompts.execute-offline",
  "providers.catalog",
  "providers.settings.save",
  "providers.credentials.clear",
  "library.prompts.execute-configured",
  "customizations.catalog",
  "themes.install",
  "themes.lifecycle",
  "extensions.activate",
  "extensions.deactivate",
  "workflows.operations.list",
  "workflows.list",
  "workflows.create",
  "workflows.get",
  "workflows.update",
  "workflows.delete",
  "workflows.plan",
  "workflows.execute",
]);
const SAFE_ERROR_CODES = new Set([
  "backend.unavailable",
  "library.invalid_input",
  "library.not_found",
  "storage.unavailable",
  "storage.invalid_database",
  "storage.future_schema",
  "workflow.storage_invalid",
  "execution.failed",
  "provider.unavailable",
  "customization.blocked",
]);
const READINESS_KEYS = [
  "applicationVersion", "capabilities", "protocolVersion", "status", "storageSchemaVersion",
];
const PROJECT_KEYS = ["createdAt", "description", "name", "projectId"];
const PROMPT_KEYS = [
  "blocks", "category", "createdAt", "projectId", "promptId", "tags", "title", "updatedAt",
];
const BLOCK_KEYS = ["blockType", "content", "enabled", "order"];

export class BackendClientError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "BackendClientError";
    this.code = code;
  }
}

export class BackendClient {
  constructor(invokeCommand = invoke, requestIdFactory = () => crypto.randomUUID()) {
    if (typeof invokeCommand !== "function" || typeof requestIdFactory !== "function") {
      throw new BackendClientError("backend.invalid_client", "Backend client is invalid.");
    }
    this.invokeCommand = invokeCommand;
    this.requestIdFactory = requestIdFactory;
  }

  checkReadiness() {
    return this.#invoke("backend_readiness", {}, validateReadiness);
  }

  listProjects() {
    return this.#invoke("library_projects", {}, validateProjectList);
  }

  createProject(name, description = "") {
    const normalizedName = validateText(name, 120, false);
    const normalizedDescription = validateText(description, 1_000, true);
    return this.#invoke(
      "library_create_project",
      { name: normalizedName, description: normalizedDescription },
      validateCreatedProject,
    );
  }

  deleteProject(projectId, confirmed) {
    const normalizedProjectId = validateIdentifier(projectId);
    requireConfirmation(confirmed);
    return this.#invoke(
      "library_delete_project",
      { projectId: normalizedProjectId, confirm: true },
      (value) => validateDeletedProject(value, normalizedProjectId),
    );
  }

  listPrompts(projectId) {
    return this.#promptCollection("library_prompts", projectId, {});
  }

  searchPrompts(projectId, query) {
    const normalizedQuery = validateText(query, 120, false);
    return this.#promptCollection("library_search_prompts", projectId, {
      query: normalizedQuery,
    });
  }

  createPrompt(projectId, title) {
    const normalizedProjectId = validateIdentifier(projectId);
    const normalizedTitle = validateText(title, 120, false);
    return this.#invoke(
      "library_create_prompt",
      { projectId: normalizedProjectId, title: normalizedTitle },
      (value) => validatePromptResult(value, normalizedProjectId),
    );
  }

  getPrompt(projectId, promptId) {
    const normalizedProjectId = validateIdentifier(projectId);
    const normalizedPromptId = validateIdentifier(promptId);
    return this.#invoke(
      "library_get_prompt",
      { projectId: normalizedProjectId, promptId: normalizedPromptId },
      (value) => validatePromptResult(value, normalizedProjectId, normalizedPromptId),
    );
  }

  updatePrompt(projectId, promptId, draft) {
    const normalizedProjectId = validateIdentifier(projectId);
    const normalizedPromptId = validateIdentifier(promptId);
    const normalizedDraft = validatePromptDraft(draft);
    return this.#invoke(
      "library_update_prompt",
      {
        projectId: normalizedProjectId,
        promptId: normalizedPromptId,
        ...normalizedDraft,
      },
      (value) => validatePromptResult(value, normalizedProjectId, normalizedPromptId),
    );
  }

  deletePrompt(projectId, promptId, confirmed) {
    const normalizedProjectId = validateIdentifier(projectId);
    const normalizedPromptId = validateIdentifier(promptId);
    requireConfirmation(confirmed);
    return this.#invoke(
      "library_delete_prompt",
      { projectId: normalizedProjectId, promptId: normalizedPromptId, confirm: true },
      (value) => validateDeletedPrompt(value, normalizedPromptId),
    );
  }


  composePrompt(projectId, promptId) {
    const normalizedProjectId = validateIdentifier(projectId);
    const normalizedPromptId = validateIdentifier(promptId);
    return this.#invoke(
      "library_compose_prompt",
      { projectId: normalizedProjectId, promptId: normalizedPromptId },
      (value) => validateComposition(value, normalizedProjectId, normalizedPromptId),
    );
  }

  executePromptOffline(projectId, promptId, confirmed) {
    const normalizedProjectId = validateIdentifier(projectId);
    const normalizedPromptId = validateIdentifier(promptId);
    requireConfirmation(confirmed);
    return this.#invoke(
      "library_execute_prompt_offline",
      {
        projectId: normalizedProjectId,
        promptId: normalizedPromptId,
        providerId: OFFLINE_REFERENCE_PROVIDER,
        confirm: true,
      },
      (value) => validateExecution(value, normalizedProjectId, normalizedPromptId),
    );
  }

  listProviders() {
    return this.#invoke("provider_catalog", {}, validateProviderCatalog);
  }

  saveProviderSettings(settings) {
    requireExactObject(settings, [
      "credential", "endpoint", "maxOutputTokens", "model", "providerId", "temperature",
    ]);
    const providerId = validateConfiguredProviderId(settings.providerId);
    if (settings.endpoint !== OPENAI_RESPONSES_ENDPOINT) {
      throw invalidProviderSettings();
    }
    const model = validateProviderModel(settings.model);
    if (
      typeof settings.temperature !== "number" || !Number.isFinite(settings.temperature) ||
      settings.temperature < 0 || settings.temperature > 2 ||
      !Number.isSafeInteger(settings.maxOutputTokens) || settings.maxOutputTokens < 1 ||
      settings.maxOutputTokens > 4_096 ||
      (settings.credential !== null && !validCredential(settings.credential))
    ) {
      throw invalidProviderSettings();
    }
    return this.#invoke(
      "provider_save_settings",
      {
        providerId,
        endpoint: OPENAI_RESPONSES_ENDPOINT,
        model,
        temperature: settings.temperature,
        maxOutputTokens: settings.maxOutputTokens,
        credential: settings.credential,
      },
      validateProviderResult,
    );
  }

  clearProviderCredential(confirmed) {
    requireConfirmation(confirmed);
    return this.#invoke(
      "provider_clear_credential",
      { providerId: OPENAI_RESPONSES_PROVIDER, confirm: true },
      validateProviderResult,
    );
  }

  executePromptConfigured(projectId, promptId, providerId, confirmed) {
    const normalizedProjectId = validateIdentifier(projectId);
    const normalizedPromptId = validateIdentifier(promptId);
    const normalizedProviderId = validateConfiguredProviderId(providerId);
    requireConfirmation(confirmed);
    return this.#invoke(
      "library_execute_prompt_configured",
      {
        projectId: normalizedProjectId,
        promptId: normalizedPromptId,
        providerId: normalizedProviderId,
        confirm: true,
      },
      (value) => validateConfiguredExecution(value, normalizedProjectId, normalizedPromptId),
    );
  }
  #promptCollection(command, projectId, payload) {
    const normalizedProjectId = validateIdentifier(projectId);
    return this.#invoke(
      command,
      { projectId: normalizedProjectId, ...payload },
      (value) => validatePromptList(value, normalizedProjectId),
    );
  }

  async #invoke(command, payload, validator) {
    const requestId = this.requestIdFactory();
    if (typeof requestId !== "string" || !REQUEST_ID.test(requestId)) {
      throw new BackendClientError(
        "library.invalid_input",
        "Library request identifier is invalid.",
      );
    }
    let response;
    try {
      response = await this.invokeCommand(command, { requestId, ...payload });
    } catch (error) {
      throw normalizeBackendError(error);
    }
    return validator(response);
  }
}

export function validateReadiness(value) {
  requireExactObject(value, READINESS_KEYS);
  if (
    value.status !== "ready" ||
    value.protocolVersion !== 1 ||
    value.storageSchemaVersion !== 1 ||
    typeof value.applicationVersion !== "string" ||
    !VERSION.test(value.applicationVersion) ||
    !Array.isArray(value.capabilities) ||
    value.capabilities.length !== CAPABILITIES.length ||
    value.capabilities.some((capability, index) => capability !== CAPABILITIES[index])
  ) {
    throw unavailable();
  }
  return Object.freeze({
    status: value.status,
    applicationVersion: value.applicationVersion,
    protocolVersion: value.protocolVersion,
    storageSchemaVersion: value.storageSchemaVersion,
    capabilities: Object.freeze([...value.capabilities]),
  });
}

export function validateProjectList(value) {
  requireExactObject(value, ["hasMore", "projects"]);
  if (typeof value.hasMore !== "boolean" || !Array.isArray(value.projects) || value.projects.length > 50) {
    throw unavailable();
  }
  return Object.freeze({
    projects: Object.freeze(value.projects.map(validateProject)),
    hasMore: value.hasMore,
  });
}

export function validatePromptList(value, projectId) {
  const expectedProjectId = validateIdentifier(projectId);
  requireExactObject(value, ["hasMore", "prompts"]);
  if (typeof value.hasMore !== "boolean" || !Array.isArray(value.prompts) || value.prompts.length > 50) {
    throw unavailable();
  }
  const prompts = value.prompts.map(validatePrompt);
  if (prompts.some((prompt) => prompt.projectId !== expectedProjectId)) {
    throw unavailable();
  }
  return Object.freeze({ prompts: Object.freeze(prompts), hasMore: value.hasMore });
}

export function validateCreatedProject(value) {
  requireExactObject(value, ["project"]);
  return Object.freeze({ project: validateProject(value.project) });
}

export function validateCreatedPrompt(value, projectId) {
  return validatePromptResult(value, projectId);
}

function validatePromptResult(value, projectId, promptId = null) {
  const expectedProjectId = validateIdentifier(projectId);
  requireExactObject(value, ["prompt"]);
  const prompt = validatePrompt(value.prompt);
  if (prompt.projectId !== expectedProjectId || (promptId !== null && prompt.promptId !== promptId)) {
    throw unavailable();
  }
  return Object.freeze({ prompt });
}

function validateDeletedProject(value, projectId) {
  requireExactObject(value, ["deletedProjectId", "deletedPromptCount"]);
  if (
    value.deletedProjectId !== projectId ||
    !Number.isSafeInteger(value.deletedPromptCount) ||
    value.deletedPromptCount < 0
  ) {
    throw unavailable();
  }
  return Object.freeze({
    deletedProjectId: value.deletedProjectId,
    deletedPromptCount: value.deletedPromptCount,
  });
}

function validateDeletedPrompt(value, promptId) {
  requireExactObject(value, ["deletedPromptId"]);
  if (value.deletedPromptId !== promptId) {
    throw unavailable();
  }
  return Object.freeze({ deletedPromptId: value.deletedPromptId });
}

function validateProject(value) {
  requireExactObject(value, PROJECT_KEYS);

  return Object.freeze({
    projectId: validateIdentifier(value.projectId),
    name: validateText(value.name, 120, false),
    description: validateText(value.description, 1_000, true),
    createdAt: validateTimestamp(value.createdAt),
  });
}

export function validateComposition(value, projectId, promptId) {
  const expectedProjectId = validateIdentifier(projectId);
  const expectedPromptId = validateIdentifier(promptId);
  requireExactObject(value, [
    "characterCount", "enabledBlockCount", "finalPrompt", "projectId", "promptId", "title",
    "totalBlockCount",
  ]);
  const finalPrompt = validateText(value.finalPrompt, 12_500, false);
  if (
    value.projectId !== expectedProjectId || value.promptId !== expectedPromptId ||
    !Number.isSafeInteger(value.enabledBlockCount) || value.enabledBlockCount < 1 ||
    !Number.isSafeInteger(value.totalBlockCount) || value.totalBlockCount < value.enabledBlockCount ||
    value.totalBlockCount > 12 || value.characterCount !== Array.from(finalPrompt).length
  ) {
    throw unavailable();
  }
  return Object.freeze({
    projectId: value.projectId,
    promptId: value.promptId,
    title: validateText(value.title, 120, false),
    finalPrompt,
    enabledBlockCount: value.enabledBlockCount,
    totalBlockCount: value.totalBlockCount,
    characterCount: value.characterCount,
  });
}

export function validateExecution(value, projectId, promptId) {
  const expectedProjectId = validateIdentifier(projectId);
  const expectedPromptId = validateIdentifier(promptId);
  requireExactObject(value, [
    "executionId", "inputUnits", "output", "outputUnits", "projectId", "promptCharacterCount",
    "promptId", "providerId", "providerVersion",
  ]);
  const output = validateText(value.output, 12_564, false);
  if (
    value.projectId !== expectedProjectId || value.promptId !== expectedPromptId ||
    value.providerId !== OFFLINE_REFERENCE_PROVIDER ||
    typeof value.providerVersion !== "string" || !VERSION.test(value.providerVersion) ||
    !Number.isSafeInteger(value.inputUnits) || value.inputUnits < 0 ||
    !Number.isSafeInteger(value.outputUnits) || value.outputUnits < 0 ||
    !Number.isSafeInteger(value.promptCharacterCount) || value.promptCharacterCount < 1 ||
    value.promptCharacterCount > 12_500
  ) {
    throw unavailable();
  }
  return Object.freeze({
    projectId: value.projectId,
    promptId: value.promptId,
    providerId: value.providerId,
    providerVersion: value.providerVersion,
    executionId: validateIdentifier(value.executionId),
    output,
    inputUnits: value.inputUnits,
    outputUnits: value.outputUnits,
    promptCharacterCount: value.promptCharacterCount,
  });
}

export function validateProviderCatalog(value) {
  requireExactObject(value, ["providers"]);
  if (!Array.isArray(value.providers) || value.providers.length !== 2) {
    throw unavailable();
  }
  const providers = value.providers.map(validateProvider);
  if (
    providers[0].providerId !== OFFLINE_REFERENCE_PROVIDER ||
    providers[1].providerId !== OPENAI_RESPONSES_PROVIDER
  ) {
    throw unavailable();
  }
  return Object.freeze({ providers: Object.freeze(providers) });
}

function validateProviderResult(value) {
  requireExactObject(value, ["provider"]);
  const provider = validateProvider(value.provider);
  if (provider.providerId !== OPENAI_RESPONSES_PROVIDER) {
    throw unavailable();
  }
  return Object.freeze({ provider });
}

function validateProvider(value) {
  requireExactObject(value, [
    "authentication", "available", "configurable", "credentialReference", "credentialState",
    "endpoint", "maxOutputTokens", "model", "name", "providerId", "temperature", "transport",
    "version",
  ]);
  const common = {
    providerId: value.providerId,
    name: validateText(value.name, 120, false),
    version: typeof value.version === "string" && VERSION.test(value.version)
      ? value.version : unavailableValue(),
    transport: value.transport,
    authentication: value.authentication,
    configurable: value.configurable,
    available: value.available,
    credentialState: value.credentialState,
    credentialReference: value.credentialReference,
    endpoint: value.endpoint,
    model: value.model,
    temperature: value.temperature,
    maxOutputTokens: value.maxOutputTokens,
  };
  if (value.providerId === OFFLINE_REFERENCE_PROVIDER) {
    if (
      value.transport !== "local" || value.authentication !== "none" || value.configurable !== false ||
      value.available !== true || value.credentialState !== "not-required" ||
      value.credentialReference !== null || value.endpoint !== null || value.model !== null ||
      value.temperature !== null || value.maxOutputTokens !== null
    ) throw unavailable();
  } else if (value.providerId === OPENAI_RESPONSES_PROVIDER) {
    if (
      value.transport !== "https" || value.authentication !== "api-key" || value.configurable !== true ||
      !["missing", "stored"].includes(value.credentialState) ||
      value.available !== (value.credentialState === "stored") ||
      value.credentialReference !== OPENAI_CREDENTIAL_REFERENCE ||
      value.endpoint !== OPENAI_RESPONSES_ENDPOINT || validateProviderModel(value.model) !== value.model ||
      typeof value.temperature !== "number" || !Number.isFinite(value.temperature) ||
      value.temperature < 0 || value.temperature > 2 || !Number.isSafeInteger(value.maxOutputTokens) ||
      value.maxOutputTokens < 1 || value.maxOutputTokens > 4_096
    ) throw unavailable();
  } else {
    throw unavailable();
  }
  return Object.freeze(common);
}

export function validateConfiguredExecution(value, projectId, promptId) {
  const expectedProjectId = validateIdentifier(projectId);
  const expectedPromptId = validateIdentifier(promptId);
  requireExactObject(value, [
    "executionId", "inputUnits", "model", "output", "outputUnits", "projectId",
    "promptCharacterCount", "promptId", "providerId", "providerVersion",
  ]);
  const output = validateText(value.output, 12_500, false);
  if (
    value.projectId !== expectedProjectId || value.promptId !== expectedPromptId ||
    value.providerId !== OPENAI_RESPONSES_PROVIDER || value.providerVersion !== "1.0.0" ||
    !Number.isSafeInteger(value.inputUnits) || value.inputUnits < 0 ||
    !Number.isSafeInteger(value.outputUnits) || value.outputUnits < 0 ||
    !Number.isSafeInteger(value.promptCharacterCount) || value.promptCharacterCount < 1 ||
    value.promptCharacterCount > 12_500
  ) throw unavailable();
  return Object.freeze({
    projectId: value.projectId, promptId: value.promptId, providerId: value.providerId,
    providerVersion: value.providerVersion, executionId: validateIdentifier(value.executionId),
    output, inputUnits: value.inputUnits, outputUnits: value.outputUnits,
    promptCharacterCount: value.promptCharacterCount, model: validateProviderModel(value.model),
  });
}

function validatePrompt(value) {
  requireExactObject(value, PROMPT_KEYS);
  const blocks = validateBlocks(value.blocks, true);
  const tags = validateTags(value.tags);
  const category = validateOptionalText(value.category, 80);
  return Object.freeze({
    promptId: validateIdentifier(value.promptId),
    projectId: validateIdentifier(value.projectId),
    title: validateText(value.title, 120, false),
    category,
    tags: Object.freeze(tags),
    blocks: Object.freeze(blocks),
    createdAt: validateTimestamp(value.createdAt),
    updatedAt: validateTimestamp(value.updatedAt),
  });
}

function validatePromptDraft(value) {
  requireExactObject(value, ["blocks", "category", "tags", "title"]);
  return Object.freeze({
    title: validateText(value.title, 120, false),
    category: validateOptionalText(value.category, 80),
    tags: validateTags(value.tags),
    blocks: validateBlocks(value.blocks, false).map(({ blockType, content, enabled }) => ({
      blockType, content, enabled,
    })),
  });
}

function validateTags(value) {
  if (!Array.isArray(value) || value.length > 10) {
    throw new BackendClientError("library.invalid_input", "Prompt tags are invalid.");
  }
  const tags = value.map((tag) => validateText(tag, 32, false));
  if (tags.some((tag) => tag.includes("\n") || tag.includes("\r"))) {
    throw new BackendClientError("library.invalid_input", "Prompt tags are invalid.");
  }
  if (new Set(tags.map((tag) => tag.toLowerCase())).size !== tags.length) {
    throw new BackendClientError("library.invalid_input", "Prompt tags are invalid.");
  }
  return tags;
}

function validateBlocks(value, requireOrder) {
  if (!Array.isArray(value) || value.length > 12) {
    throw new BackendClientError("library.invalid_input", "Prompt blocks are invalid.");
  }
  let total = 0;
  return value.map((block, index) => {
    requireExactObject(block, requireOrder ? BLOCK_KEYS : ["blockType", "content", "enabled"]);
    if (!BLOCK_TYPES.has(block.blockType) || typeof block.enabled !== "boolean") {
      throw new BackendClientError("library.invalid_input", "Prompt blocks are invalid.");
    }
    if (requireOrder && block.order !== index) {
      throw unavailable();
    }
    const content = validateText(block.content, 2_000, false);
    total += content.length;
    if (total > 12_000) {
      throw new BackendClientError("library.invalid_input", "Prompt blocks are invalid.");
    }
    return Object.freeze({ blockType: block.blockType, content, order: index, enabled: block.enabled });
  });
}

function requireConfirmation(value) {
  if (value !== true) {
    throw new BackendClientError("library.invalid_input", "Operation requires confirmation.");
  }
}

function validateIdentifier(value) {
  if (typeof value !== "string" || !IDENTIFIER.test(value)) {
    throw new BackendClientError("library.invalid_input", "Library identifier is invalid.");
  }
  return value;
}

function validateOptionalText(value, maximum) {
  if (value === null) {
    return null;
  }
  const normalized = validateText(value, maximum, true);
  return normalized || null;
}

function validateText(value, maximum, allowEmpty) {
  if (typeof value !== "string") {
    throw new BackendClientError("library.invalid_input", "Library information is invalid.");
  }
  const normalized = value.trim();
  if (normalized.length > maximum || (!allowEmpty && normalized.length === 0)) {
    throw new BackendClientError("library.invalid_input", "Library information is invalid.");
  }
  return normalized;
}

function validateTimestamp(value) {
  if (typeof value !== "string" || !TIMESTAMP.test(value) || Number.isNaN(Date.parse(value))) {
    throw unavailable();
  }
  return value;
}

function requireExactObject(value, keys) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw unavailable();
  }
  if (Object.keys(value).sort().join(",") !== [...keys].sort().join(",")) {
    throw unavailable();
  }
}

function validateConfiguredProviderId(value) {
  if (value !== OPENAI_RESPONSES_PROVIDER) {
    throw invalidProviderSettings();
  }
  return value;
}

function validateProviderModel(value) {
  if (
    typeof value !== "string" || value.length < 1 || value.length > 80 ||
    !/^[A-Za-z0-9][A-Za-z0-9._:-]*$/.test(value)
  ) {
    throw invalidProviderSettings();
  }
  return value;
}

function validCredential(value) {
  return typeof value === "string" && value.length >= 8 && value.length <= 512 &&
    value.trim() === value && !/[\u0000-\u001f\u007f]/.test(value);
}

function invalidProviderSettings() {
  return new BackendClientError("library.invalid_input", "Provider settings are invalid.");
}

function unavailableValue() {
  throw unavailable();
}

function normalizeBackendError(value) {
  if (
    value !== null && typeof value === "object" && !Array.isArray(value) &&
    SAFE_ERROR_CODES.has(value.code) && typeof value.message === "string" &&
    value.message.length > 0 && value.message.length <= 256
  ) {
    return new BackendClientError(value.code, value.message);
  }
  return unavailable();
}

function unavailable() {
  return new BackendClientError(
    "backend.unavailable",
    "The local application backend is unavailable.",
  );
}
