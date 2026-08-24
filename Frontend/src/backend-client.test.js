import assert from "node:assert/strict";
import test from "node:test";

import {
  BackendClient,
  BackendClientError,
  validateReadiness,
} from "./backend-client.js";

const ready = Object.freeze({
  status: "ready",
  applicationVersion: "0.2.0-alpha",
  protocolVersion: 1,
  capabilities: ["application.readiness"],
});

test("client invokes only the readiness command with one correlated request id", async () => {
  const calls = [];
  const client = new BackendClient(async (...args) => {
    calls.push(args);
    return ready;
  }, () => "550e8400-e29b-41d4-a716-446655440000");

  const result = await client.checkReadiness();

  assert.deepEqual(calls, [["backend_readiness", {
    requestId: "550e8400-e29b-41d4-a716-446655440000",
  }]]);
  assert.deepEqual(result, ready);
  assert.ok(Object.isFrozen(result));
  assert.ok(Object.isFrozen(result.capabilities));
});

test("client rejects invalid generated request identifiers before invoke", async () => {
  let called = false;
  const client = new BackendClient(async () => {
    called = true;
    return ready;
  }, () => "bad id");

  await assert.rejects(() => client.checkReadiness(), /identifier is invalid/);
  assert.equal(called, false);
});

test("readiness validation rejects extra, missing, and malformed data", () => {
  const cases = [
    null,
    { ...ready, extra: true },
    { ...ready, status: "starting" },
    { ...ready, applicationVersion: "latest" },
    { ...ready, protocolVersion: 2 },
    { ...ready, capabilities: [] },
    { ...ready, capabilities: ["application.readiness", "python.eval"] },
  ];

  for (const value of cases) {
    assert.throws(() => validateReadiness(value), BackendClientError);
  }
});

test("structured backend failures remain bounded", async () => {
  const client = new BackendClient(async () => {
    throw { code: "backend.unavailable", message: "Backend did not start." };
  }, () => "request-1");

  await assert.rejects(
    () => client.checkReadiness(),
    new BackendClientError("backend.unavailable", "Backend did not start."),
  );
});

test("untyped or oversized rejection values collapse to one safe failure", async () => {
  for (const value of [new Error("secret path"), "raw failure", null, {
    code: "x".repeat(65),
    message: "unsafe",
  }]) {
    const client = new BackendClient(async () => {
      throw value;
    }, () => "request-1");
    await assert.rejects(
      () => client.checkReadiness(),
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

