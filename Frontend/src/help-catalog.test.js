import assert from "node:assert/strict";
import test from "node:test";

import { HELP_TOPICS, helpCategories, helpTopic, searchHelpTopics } from "./help-catalog.js";

test("help catalog is fixed, complete, and internally linked", () => {
  assert.equal(HELP_TOPICS.length, 15);
  assert.ok(Object.isFrozen(HELP_TOPICS));
  assert.deepEqual(helpCategories(), ["Essentials", "Running work", "Advanced", "Manage the app", "Testing", "Help"]);

  const ids = new Set();
  for (const topic of HELP_TOPICS) {
    assert.match(topic.id, /^[a-z][a-z0-9-]{2,39}$/);
    assert.ok(!ids.has(topic.id));
    ids.add(topic.id);
    assert.ok(topic.title.length >= 8 && topic.title.length <= 80);
    assert.ok(topic.summary.length >= 20 && topic.summary.length <= 180);
    assert.ok(topic.outcome.length >= 20 && topic.outcome.length <= 160);
    assert.ok(topic.steps.length >= 4 && topic.steps.length <= 9);
    assert.ok(Object.isFrozen(topic));
    assert.ok(Object.isFrozen(topic.steps));
    for (const step of topic.steps) {
      assert.ok(step.title.length >= 3 && step.title.length <= 80);
      assert.ok(step.body.length >= 10 && step.body.length <= 300);
      assert.ok(Object.isFrozen(step));
    }
  }

  for (const topic of HELP_TOPICS) {
    for (const relatedId of topic.related) assert.ok(ids.has(relatedId), `${topic.id} links to ${relatedId}`);
  }
});

test("help topic lookup is exact and returns null for unknown inputs", () => {
  assert.equal(helpTopic("getting-started")?.title, "Start here: your first 10 minutes");
  assert.equal(helpTopic("Getting-Started"), null);
  assert.equal(helpTopic("unknown"), null);
  assert.equal(helpTopic(null), null);
});

test("empty help search returns the frozen catalog in authored order", () => {
  assert.equal(searchHelpTopics(""), HELP_TOPICS);
  assert.equal(searchHelpTopics("   "), HELP_TOPICS);
  assert.equal(searchHelpTopics(null), HELP_TOPICS);
});

test("help search matches keywords, task text, and all entered terms", () => {
  assert.deepEqual(searchHelpTopics("API key").map((topic) => topic.id), ["openai-provider"]);
  assert.ok(searchHelpTopics("cycles duplicate").some((topic) => topic.id === "workflows"));
  assert.ok(searchHelpTopics("SmartScreen").some((topic) => topic.id === "distribution"));
  assert.deepEqual(searchHelpTopics("a phrase that does not exist"), []);
});

test("help search is case and accent insensitive without mutating topics", () => {
  const before = JSON.stringify(HELP_TOPICS);
  assert.ok(searchHelpTopics("OPENAI RESPONSES").some((topic) => topic.id === "openai-provider"));
  assert.ok(searchHelpTopics("deterministic").some((topic) => topic.id === "workflows"));
  assert.equal(JSON.stringify(HELP_TOPICS), before);
});
