import { invoke } from "@tauri-apps/api/core";

const REQUEST_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/;
const VERSION = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/;
const READINESS_KEYS = [
  "applicationVersion",
  "capabilities",
  "protocolVersion",
  "status",
];

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

  async checkReadiness() {
    const requestId = this.requestIdFactory();
    if (typeof requestId !== "string" || !REQUEST_ID.test(requestId)) {
      throw new BackendClientError(
        "backend.invalid_request",
        "Backend request identifier is invalid.",
      );
    }
    let response;
    try {
      response = await this.invokeCommand("backend_readiness", { requestId });
    } catch (error) {
      throw normalizeBackendError(error);
    }
    return validateReadiness(response);
  }
}

export function validateReadiness(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw unavailable();
  }
  if (Object.keys(value).sort().join(",") !== READINESS_KEYS.join(",")) {
    throw unavailable();
  }
  if (
    value.status !== "ready" ||
    value.protocolVersion !== 1 ||
    typeof value.applicationVersion !== "string" ||
    !VERSION.test(value.applicationVersion) ||
    !Array.isArray(value.capabilities) ||
    value.capabilities.length !== 1 ||
    value.capabilities[0] !== "application.readiness"
  ) {
    throw unavailable();
  }
  return Object.freeze({
    status: value.status,
    applicationVersion: value.applicationVersion,
    protocolVersion: value.protocolVersion,
    capabilities: Object.freeze([...value.capabilities]),
  });
}

function normalizeBackendError(value) {
  if (
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    typeof value.code === "string" &&
    value.code.length <= 64 &&
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

