import assert from "node:assert/strict";
import test from "node:test";

import {
  BackendClient,
  BackendClientError,
  validateCreatedProject,
  validateCreatedPrompt,
  validateProjectList,
  validatePromptList,
  validateReadiness,
} from "./backend-client.js";

const projectId = "550e8400-e29b-41d4-a716-446655440000";
const promptId = "76c7169d-9e5d-4db4-bf61-856695d2a91e";
const createdAt = "2026-08-26T00:00:00Z";
const capabilities = [
  "application.readiness",
  "library.projects.list",
  "library.projects.create",
  "library.prompts.list",
  "library.prompts.create",
];
const ready = Object.freeze({
  status: "ready",
  applicationVersion: "0.2.0-alpha",
  protocolVersion: 1,
  storageSchemaVersion: 1,
  capabilities,
});
const project = Object.freeze({
  projectId,
  name: "UPS",
  description: "Offline library",
  createdAt,
});
const prompt = Object.freeze({
  promptId,
  projectId,
  title: "Architecture",
  createdAt,
  updatedAt: createdAt,
});

test("client invokes only the five fixed library commands", async () => {
  const calls = [];
  const responses = [
    ready,
    { projects: [project], hasMore: false },
    { project },
    { prompts: [prompt], hasMore: false },
    { prompt },
  ];
  let request = 0;
  const client = new BackendClient(async (...args) => {
    calls.push(args);
    return responses[request++];
  }, () => `request-${request + 1}`);

  await client.checkReadiness();
  await client.listProjects();
  await client.createProject(" UPS ", " Offline library ");
  await client.listPrompts(projectId);
  await client.createPrompt(projectId, " Architecture ");

  assert.deepEqual(calls, [
    ["backend_readiness", { requestId: "request-1" }],
    ["library_projects", { requestId: "request-2" }],
    ["library_create_project", {
      requestId: "request-3",
      name: "UPS",
      description: "Offline library",
    }],
    ["library_prompts", { requestId: "request-4", projectId }],
    ["library_create_prompt", {
      requestId: "request-5",
      projectId,
      title: "Architecture",
    }],
  ]);
});

test("client rejects invalid inputs before invoking Tauri", async () => {
  let called = false;
  const client = new BackendClient(async () => {
    called = true;
  }, () => "bad id");

  await assert.rejects(() => client.checkReadiness(), /identifier is invalid/);
  assert.throws(
    () => new BackendClient(async () => ready, () => "request-1").createProject("   "),
    BackendClientError,
  );
  assert.throws(
    () => new BackendClient(async () => ready, () => "request-1").listPrompts("../db"),
    BackendClientError,
  );
  assert.equal(called, false);
});

test("readiness requires exact storage version and capabilities", () => {
  assert.deepEqual(validateReadiness(ready), ready);
  for (const value of [
    { ...ready, extra: true },
    { ...ready, storageSchemaVersion: 2 },
    { ...ready, capabilities: capabilities.slice(0, 1) },
  ]) {
    assert.throws(() => validateReadiness(value), BackendClientError);
  }
});

test("project lists and create results are exact, bounded, and frozen", () => {
  const listed = validateProjectList({ projects: [project], hasMore: false });
  const created = validateCreatedProject({ project });

  assert.deepEqual(listed.projects, [project]);
  assert.deepEqual(created.project, project);
  assert.ok(Object.isFrozen(listed));
  assert.ok(Object.isFrozen(listed.projects));
  assert.ok(Object.isFrozen(listed.projects[0]));
  assert.throws(
    () => validateProjectList({ projects: Array(51).fill(project), hasMore: true }),
    BackendClientError,
  );
});

test("prompt responses must remain inside the requested project", () => {
  const listed = validatePromptList({ prompts: [prompt], hasMore: false }, projectId);
  const created = validateCreatedPrompt({ prompt }, projectId);

  assert.deepEqual(listed.prompts, [prompt]);
  assert.deepEqual(created.prompt, prompt);
  assert.throws(
    () => validatePromptList(
      { prompts: [{ ...prompt, projectId: "ba9fc9fc-71a1-411c-9d54-cf6a9c3f5233" }], hasMore: false },
      projectId,
    ),
    BackendClientError,
  );
});

test("validators reject extra, missing, malformed, and unbounded data", () => {
  const malformedProjects = [
    null,
    { projects: [] },
    { projects: [], hasMore: false, extra: true },
    { projects: [{ ...project, projectId: "bad" }], hasMore: false },
    { projects: [{ ...project, createdAt: "yesterday" }], hasMore: false },
  ];
  for (const value of malformedProjects) {
    assert.throws(() => validateProjectList(value), BackendClientError);
  }
  assert.throws(() => validateCreatedPrompt({ prompt, extra: true }, projectId), BackendClientError);
});

test("only allowlisted bounded backend errors reach presentation code", async () => {
  const allowed = new BackendClient(async () => {
    throw { code: "storage.future_schema", message: "Upgrade required." };
  }, () => "request-1");
  await assert.rejects(
    () => allowed.listProjects(),
    new BackendClientError("storage.future_schema", "Upgrade required."),
  );

  for (const value of [
    new Error("secret path"),
    { code: "python.traceback", message: "secret" },
    { code: "storage.unavailable", message: "x".repeat(257) },
  ]) {
    const client = new BackendClient(async () => {
      throw value;
    }, () => "request-1");
    await assert.rejects(
      () => client.listProjects(),
      new BackendClientError(
        "backend.unavailable",
        "The local application backend is unavailable.",
      ),
    );
  }
});

test("client constructor rejects invalid adapters", () => {
  assert.throws(() => new BackendClient(null), BackendClientError);
  assert.throws(() => new BackendClient(async () => ready, null), BackendClientError);
});
