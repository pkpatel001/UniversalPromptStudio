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
  "library.projects.delete",
  "library.prompts.list",
  "library.prompts.create",
  "library.prompts.get",
  "library.prompts.update",
  "library.prompts.delete",
  "library.prompts.search",
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
  category: "Engineering",
  tags: ["offline"],
  blocks: [{ blockType: "role", content: "Architect", order: 0, enabled: true }],
  createdAt,
  updatedAt: createdAt,
});

test("client invokes only the ten fixed library commands", async () => {
  const calls = [];
  const responses = [
    ready,
    { projects: [project], hasMore: false },
    { project },
    { deletedProjectId: projectId, deletedPromptCount: 1 },
    { prompts: [prompt], hasMore: false },
    { prompt },
    { prompt },
    { prompt },
    { deletedPromptId: promptId },
    { prompts: [prompt], hasMore: false },
  ];
  let request = 0;
  const client = new BackendClient(async (...args) => {
    calls.push(args);
    return responses[request++];
  }, () => `request-${request + 1}`);

  await client.checkReadiness();
  await client.listProjects();
  await client.createProject(" UPS ", " Offline library ");
  await client.deleteProject(projectId, true);
  await client.listPrompts(projectId);
  await client.createPrompt(projectId, " Architecture ");
  await client.getPrompt(projectId, promptId);
  await client.updatePrompt(projectId, promptId, {
    title: " Architecture ",
    category: " Engineering ",
    tags: ["offline"],
    blocks: [{ blockType: "role", content: " Architect ", enabled: true }],
  });
  await client.deletePrompt(projectId, promptId, true);
  await client.searchPrompts(projectId, " architect ");

  assert.deepEqual(calls, [
    ["backend_readiness", { requestId: "request-1" }],
    ["library_projects", { requestId: "request-2" }],
    ["library_create_project", {
      requestId: "request-3", name: "UPS", description: "Offline library",
    }],
    ["library_delete_project", { requestId: "request-4", projectId, confirm: true }],
    ["library_prompts", { requestId: "request-5", projectId }],
    ["library_create_prompt", {
      requestId: "request-6", projectId, title: "Architecture",
    }],
    ["library_get_prompt", { requestId: "request-7", projectId, promptId }],
    ["library_update_prompt", {
      requestId: "request-8",
      projectId,
      promptId,
      title: "Architecture",
      category: "Engineering",
      tags: ["offline"],
      blocks: [{ blockType: "role", content: "Architect", enabled: true }],
    }],
    ["library_delete_prompt", {
      requestId: "request-9", projectId, promptId, confirm: true,
    }],
    ["library_search_prompts", {
      requestId: "request-10", projectId, query: "architect",
    }],
  ]);
});

test("client rejects invalid inputs before invoking Tauri", async () => {
  let called = false;
  const client = new BackendClient(async () => {
    called = true;
  }, () => "bad id");

  await assert.rejects(() => client.checkReadiness(), /identifier is invalid/);
  const validClient = new BackendClient(async () => ready, () => "request-1");
  assert.throws(() => validClient.createProject("   "), BackendClientError);
  assert.throws(() => validClient.listPrompts("../db"), BackendClientError);
  assert.throws(() => validClient.deleteProject(projectId, false), BackendClientError);
  assert.throws(
    () => validClient.updatePrompt(projectId, promptId, {
      title: "Prompt", category: null, tags: ["same", "SAME"], blocks: [],
    }),
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

test("prompt responses are detailed, frozen, ordered, and project scoped", () => {
  const listed = validatePromptList({ prompts: [prompt], hasMore: false }, projectId);
  const created = validateCreatedPrompt({ prompt }, projectId);

  assert.deepEqual(listed.prompts, [prompt]);
  assert.deepEqual(created.prompt, prompt);
  assert.ok(Object.isFrozen(listed.prompts[0].blocks));
  assert.ok(Object.isFrozen(listed.prompts[0].blocks[0]));
  assert.throws(
    () => validatePromptList(
      { prompts: [{ ...prompt, projectId: "ba9fc9fc-71a1-411c-9d54-cf6a9c3f5233" }], hasMore: false },
      projectId,
    ),
    BackendClientError,
  );
  assert.throws(
    () => validatePromptList({
      prompts: [{ ...prompt, blocks: [{ ...prompt.blocks[0], order: 1 }] }],
      hasMore: false,
    }, projectId),
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
  assert.throws(
    () => validateCreatedPrompt({ prompt: { ...prompt, tags: Array(11).fill("tag") } }, projectId),
    BackendClientError,
  );
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
