import { invoke } from "@tauri-apps/api/core";

const REQUEST_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/;
const IDENTIFIER = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const VERSION = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/;
const TIMESTAMP = /^\d{4}-\d{2}-\d{2}T[^\s]{8,28}Z$/;
const CAPABILITIES = Object.freeze([
  "application.readiness",
  "library.projects.list",
  "library.projects.create",
  "library.prompts.list",
  "library.prompts.create",
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
  "applicationVersion",
  "capabilities",
  "protocolVersion",
  "status",
  "storageSchemaVersion",
];
const PROJECT_KEYS = ["createdAt", "description", "name", "projectId"];
const PROMPT_KEYS = ["createdAt", "projectId", "promptId", "title", "updatedAt"];

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

  listPrompts(projectId) {
    const normalizedProjectId = validateIdentifier(projectId);
    return this.#invoke(
      "library_prompts",
      { projectId: normalizedProjectId },
      (value) => validatePromptList(value, normalizedProjectId),
    );
  }

  createPrompt(projectId, title) {
    const normalizedProjectId = validateIdentifier(projectId);
    const normalizedTitle = validateText(title, 120, false);
    return this.#invoke(
      "library_create_prompt",
      { projectId: normalizedProjectId, title: normalizedTitle },
      (value) => validateCreatedPrompt(value, normalizedProjectId),
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
  if (typeof value.hasMore !== "boolean" || !Array.isArray(value.projects)) {
    throw unavailable();
  }
  if (value.projects.length > 50) {
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
  if (typeof value.hasMore !== "boolean" || !Array.isArray(value.prompts)) {
    throw unavailable();
  }
  if (value.prompts.length > 50) {
    throw unavailable();
  }
  const prompts = value.prompts.map(validatePrompt);
  if (prompts.some((prompt) => prompt.projectId !== expectedProjectId)) {
    throw unavailable();
  }
  return Object.freeze({
    prompts: Object.freeze(prompts),
    hasMore: value.hasMore,
  });
}

export function validateCreatedProject(value) {
  requireExactObject(value, ["project"]);
  return Object.freeze({ project: validateProject(value.project) });
}

export function validateCreatedPrompt(value, projectId) {
  const expectedProjectId = validateIdentifier(projectId);
  requireExactObject(value, ["prompt"]);
  const prompt = validatePrompt(value.prompt);
  if (prompt.projectId !== expectedProjectId) {
    throw unavailable();
  }
  return Object.freeze({ prompt });
}

function validateProject(value) {
  requireExactObject(value, PROJECT_KEYS);
  const projectId = validateIdentifier(value.projectId);
  const name = validateText(value.name, 120, false);
  const description = validateText(value.description, 1_000, true);
  const createdAt = validateTimestamp(value.createdAt);
  return Object.freeze({ projectId, name, description, createdAt });
}

function validatePrompt(value) {
  requireExactObject(value, PROMPT_KEYS);
  const promptId = validateIdentifier(value.promptId);
  const projectId = validateIdentifier(value.projectId);
  const title = validateText(value.title, 120, false);
  const createdAt = validateTimestamp(value.createdAt);
  const updatedAt = validateTimestamp(value.updatedAt);
  return Object.freeze({ promptId, projectId, title, createdAt, updatedAt });
}

function validateIdentifier(value) {
  if (typeof value !== "string" || !IDENTIFIER.test(value)) {
    throw new BackendClientError("library.invalid_input", "Project identifier is invalid.");
  }
  return value;
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
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    SAFE_ERROR_CODES.has(value.code) &&
    typeof value.message === "string" &&
    value.message.length > 0 &&
    value.message.length <= 256
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
