import "./help.css";
import { HELP_TOPICS, helpCategories, helpTopic, searchHelpTopics } from "./help-catalog.js";

export function initializeHelpUI({ trigger }) {
  if (!(trigger instanceof HTMLElement)) throw new TypeError("Help UI requires a trigger.");
  const dialog = document.createElement("dialog");
  dialog.className = "help-dialog";
  dialog.setAttribute("aria-labelledby", "help-title");
  dialog.innerHTML = markup();
  document.body.append(dialog);

  const search = dialog.querySelector("#help-search");
  const results = dialog.querySelector("#help-results");
  const article = dialog.querySelector("#help-article");
  const status = dialog.querySelector("#help-search-status");
  let selectedId = "getting-started";

  function renderResults(topics) {
    results.replaceChildren();
    status.textContent = `${topics.length} help topic${topics.length === 1 ? "" : "s"}`;
    if (!topics.length) {
      const empty = document.createElement("p");
      empty.className = "help-empty";
      empty.textContent = "No topics match. Try a task such as import, workflow, API key, or install.";
      results.append(empty);
      return;
    }
    const groups = new Map();
    for (const topic of topics) {
      if (!groups.has(topic.category)) groups.set(topic.category, []);
      groups.get(topic.category).push(topic);
    }
    for (const category of helpCategories()) {
      const matches = groups.get(category);
      if (!matches) continue;
      const section = document.createElement("section");
      const heading = document.createElement("h3");
      heading.textContent = category;
      const list = document.createElement("div");
      list.className = "help-topic-list";
      for (const topic of matches) {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.topicId = topic.id;
        button.className = topic.id === selectedId ? "active" : "";
        button.setAttribute("aria-current", topic.id === selectedId ? "page" : "false");
        const title = document.createElement("strong");
        title.textContent = topic.title;
        const summary = document.createElement("span");
        summary.textContent = topic.summary;
        button.append(title, summary);
        list.append(button);
      }
      section.append(heading, list);
      results.append(section);
    }
  }

  function renderArticle(id) {
    const topic = helpTopic(id) ?? HELP_TOPICS[0];
    selectedId = topic.id;
    article.replaceChildren();

    const eyebrow = element("p", "help-eyebrow", topic.category);
    const heading = element("h2", "", topic.title);
    heading.tabIndex = -1;
    const summary = element("p", "help-summary", topic.summary);
    const outcome = element("div", "help-outcome", `Outcome: ${topic.outcome}`);
    article.append(eyebrow, heading, summary, outcome);

    if (topic.beforeStart.length) {
      article.append(sectionList("Before you start", topic.beforeStart));
    }
    const stepsSection = document.createElement("section");
    stepsSection.append(element("h3", "", "Follow these steps"));
    const steps = document.createElement("ol");
    steps.className = "help-steps";
    for (const step of topic.steps) {
      const item = document.createElement("li");
      item.append(element("strong", "", step.title), element("p", "", step.body));
      steps.append(item);
    }
    stepsSection.append(steps);
    article.append(stepsSection, sectionList("Useful tips", topic.tips));

    if (topic.related.length) {
      const related = document.createElement("section");
      related.className = "help-related";
      related.append(element("h3", "", "Related topics"));
      const links = document.createElement("div");
      for (const relatedId of topic.related) {
        const relatedTopic = helpTopic(relatedId);
        const button = document.createElement("button");
        button.type = "button";
        button.className = "secondary";
        button.dataset.topicId = relatedId;
        button.textContent = relatedTopic.title;
        links.append(button);
      }
      related.append(links);
      article.append(related);
    }
    renderResults(searchHelpTopics(search.value));
    article.scrollTop = 0;
    heading.focus({ preventScroll: true });
  }

  function open(id = "getting-started") {
    search.value = "";
    renderArticle(helpTopic(id) ? id : "getting-started");
    if (!dialog.open) dialog.showModal();
  }

  trigger.addEventListener("click", () => open(trigger.dataset.helpTopic));
  document.addEventListener("click", (event) => {
    const contextual = event.target.closest("[data-help-topic]");
    if (!contextual || contextual === trigger) return;
    open(contextual.dataset.helpTopic);
  });
  dialog.querySelector("[data-help-close]").addEventListener("click", () => dialog.close());
  search.addEventListener("input", () => renderResults(searchHelpTopics(search.value)));
  results.addEventListener("click", (event) => {
    const button = event.target.closest("[data-topic-id]");
    if (button) renderArticle(button.dataset.topicId);
  });
  article.addEventListener("click", (event) => {
    const button = event.target.closest("[data-topic-id]");
    if (button) renderArticle(button.dataset.topicId);
  });

  renderResults(HELP_TOPICS);
  return Object.freeze({ open, close: () => dialog.close() });
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = text;
  return node;
}

function sectionList(title, values) {
  const section = document.createElement("section");
  section.append(element("h3", "", title));
  const list = document.createElement("ul");
  for (const value of values) list.append(element("li", "", value));
  section.append(list);
  return section;
}

function markup() {
  return `<div class="help-shell">
    <header class="help-header"><div><p>Offline user guide</p><h2 id="help-title">Help &amp; learning</h2></div><button class="secondary" type="button" data-help-close>Close</button></header>
    <div class="help-layout"><aside class="help-browser" aria-label="Help topics">
      <label for="help-search">What do you want to do?<input id="help-search" type="search" maxlength="100" placeholder="Try: create a prompt"></label>
      <p id="help-search-status" class="help-search-status" role="status" aria-live="polite"></p>
      <div id="help-results" class="help-results"></div>
    </aside><article id="help-article" class="help-article"></article></div>
  </div>`;
}
