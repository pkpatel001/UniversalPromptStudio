import { invoke } from "@tauri-apps/api/core";

const REQUEST_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/;
const IDENTIFIER = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const VERSION = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/;
const TIMESTAMP = /^\d{4}-\d{2}-\d{2}T[^\s]{8,28}Z$/;
const BLOCK_TYPES = new Set([
  "role", "goal", "context", "audience", "constraints", "requirements", "tone",
  "output_format", "reasoning_style", "examples", "validation_rules", "final_instructions",
]);
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
]);
const SAFE_ERROR_CODES = new Set([
  "backend.unavailable",
  "library.invalid_input",
  "library.not_found",
  "storage.unavailable",
  "storage.invalid_database",
  "storage.future_schema",
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
    throw new BackendClientError("library.invalid_input", "Deletion requires confirmation.");
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
