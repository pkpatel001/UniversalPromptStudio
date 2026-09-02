const rawTopics = [
  {
    id: "getting-started",
    title: "Start here: your first 10 minutes",
    category: "Essentials",
    summary: "Create a project, save a block-based prompt, preview it, and run the offline reference provider.",
    outcome: "You will have one reusable prompt and a safe local test result.",
    beforeStart: ["Install and open Universal Prompt Studio.", "Complete the short first-run welcome screen."],
    steps: [
      ["Create a project", "In the left sidebar, enter a project name and choose Create project. Projects keep related prompts together."],
      ["Create a prompt", "Select the project, enter a prompt title, and choose Create prompt."],
      ["Add useful blocks", "Add Role, Goal, Context, Constraints, and Output format blocks. Write one clear instruction in each block and keep the blocks enabled."],
      ["Save and preview", "Choose Save prompt, then Compose preview. The preview shows the exact enabled blocks in their current order."],
      ["Run safely", "Select Offline reference, choose Run composed prompt, and confirm. This local echo path is ideal for checking composition without contacting an AI service."],
    ],
    tips: ["Start with a small prompt before adding examples or advanced constraints.", "Nothing runs in the background; runs require an explicit action and confirmation."],
    related: ["projects", "prompts", "prompt-blocks", "compose-run"],
    keywords: ["beginner", "quick start", "first prompt", "tutorial", "offline"],
  },
  {
    id: "projects",
    title: "Projects and organization",
    category: "Essentials",
    summary: "Use projects as local folders for prompts that belong to the same client, product, or kind of work.",
    outcome: "Your prompt library will stay understandable as it grows.",
    beforeStart: ["Decide on a simple grouping such as Client, Product, Team, or Personal."],
    steps: [
      ["Create", "Use the form in the left sidebar. A short, specific project name is easiest to scan."],
      ["Select", "Choose a project to open its prompt library. Search and prompt creation apply to that selected project."],
      ["Describe", "Add a project description so future you knows what belongs there."],
      ["Delete carefully", "Delete project removes that project and its prompts after confirmation. Export important prompts first when you need a portable copy."],
    ],
    tips: ["Prefer a few meaningful projects over one project per prompt.", "Use prompt categories and tags for finer organization inside a project."],
    related: ["prompts", "portability"],
    keywords: ["folder", "library", "organize", "delete project", "categories", "tags"],
  },
  {
    id: "prompts",
    title: "Create, edit, find, and delete prompts",
    category: "Essentials",
    summary: "Build a reusable prompt record, label it, search it, and keep changes intentionally saved.",
    outcome: "You can maintain a useful prompt library instead of copying text between tools.",
    beforeStart: ["Select or create a project."],
    steps: [
      ["Create", "Enter a title in the project toolbar and choose Create prompt."],
      ["Describe and label", "Add a description, category, and comma-separated tags that will help you recognize and search for the prompt."],
      ["Build", "Add ordered prompt blocks and write one kind of instruction per block."],
      ["Save", "Choose Save prompt after editing. Composition and execution use the saved enabled blocks."],
      ["Find", "Use project-scoped search to match prompt titles and indexed prompt information."],
      ["Delete", "Choose Delete only when the correct prompt is open and confirm the action."],
    ],
    tips: ["Use outcome-oriented titles such as Draft release notes rather than Prompt 7.", "Duplicate ideas can be exported and re-imported with a reviewed conflict action."],
    related: ["prompt-blocks", "compose-run", "portability"],
    keywords: ["create prompt", "edit", "save", "search", "delete", "title", "category", "tag"],
  },
  {
    id: "prompt-blocks",
    title: "Prompt blocks: what each one does",
    category: "Essentials",
    summary: "Separate a prompt into ordered, reusable instructions so its purpose and constraints are easy to review.",
    outcome: "You can choose the right block types and control the final prompt order.",
    beforeStart: ["Open a prompt in the editor."],
    steps: [
      ["Role and goal", "Use Role for the needed perspective or expertise and Goal for the single result to accomplish."],
      ["Constraints and requirements", "Use Constraints for boundaries and exclusions, and Requirements for mandatory details the result must include."],
      ["Context and audience", "Supply necessary background and identify who will use the result."],
      ["Tone and reasoning style", "Specify the communication tone and, when useful, the approach the assistant should use to develop the answer."],
      ["Examples", "Provide small representative examples that clarify the desired pattern without replacing the actual instructions."],
      ["Output format", "Define the exact response structure, field order, headings, or length."],
      ["Validation rules and final instructions", "State observable acceptance checks, then place any final priority or reminder in Final instructions."],
      ["Order and enablement", "Reorder blocks to control composition. Disable a block to omit it without deleting it."],
    ],
    tips: ["Keep each block focused; mixed instructions are harder to debug.", "Treat examples as guidance and constraints as requirements."],
    related: ["prompts", "compose-run", "stress-testing"],
    keywords: ["role", "goal", "context", "audience", "constraints", "requirements", "tone", "reasoning style", "examples", "output format", "validation rules", "final instructions", "reorder", "enabled"],
  },
  {
    id: "compose-run",
    title: "Compose, preview, and run a prompt",
    category: "Running work",
    summary: "Inspect the exact saved prompt before sending it through a selected provider.",
    outcome: "You can distinguish prompt composition from provider execution and run deliberately.",
    beforeStart: ["Save a prompt with at least one enabled block."],
    steps: [
      ["Compose preview", "Choose Compose preview to assemble saved enabled blocks in order. Review the displayed text before running."],
      ["Choose a provider", "Use Offline reference for local composition tests or OpenAI Responses after configuring a credential."],
      ["Review options", "Provider controls are bounded to the options shown by the application."],
      ["Run and confirm", "Choose Run composed prompt and confirm. The application performs one explicit foreground run."],
      ["Read the result", "Review either the provider output or the safe error. Correct the prompt, provider setup, or input and retry intentionally."],
    ],
    tips: ["A good preview is necessary but does not guarantee a good model response.", "Use the offline provider during editing to avoid external calls."],
    related: ["openai-provider", "privacy-security", "stress-testing"],
    keywords: ["compose", "preview", "run", "execute", "provider", "offline echo", "result", "confirmation"],
  },
  {
    id: "openai-provider",
    title: "Configure the OpenAI provider",
    category: "Running work",
    summary: "Store a credential for the current Windows user and make explicit calls to the fixed OpenAI Responses endpoint.",
    outcome: "You can run a composed prompt through the supported OpenAI path with clear boundaries.",
    beforeStart: ["Have an OpenAI API key and understand that API usage may incur charges.", "Use the offline provider first to verify your prompt composition."],
    steps: [
      ["Select OpenAI Responses", "Open the provider controls and select the OpenAI Responses provider."],
      ["Save the credential", "Enter the API key and save it. Windows DPAPI protects it for the current Windows user; the application does not display it again."],
      ["Choose supported options", "Select only the model and bounded options exposed by the interface. The API endpoint is fixed by the host."],
      ["Run explicitly", "Preview the prompt, run it, and confirm the external provider action."],
      ["Clear when needed", "Use Clear credential to remove the saved provider secret from this device profile."],
    ],
    tips: ["Never place an API key inside prompt content or a portable file.", "Provider credentials are excluded from application exports and support snapshots."],
    related: ["compose-run", "privacy-security", "troubleshooting"],
    keywords: ["openai", "api key", "credential", "dpapi", "responses", "model", "endpoint", "billing", "external"],
  },
  {
    id: "workflows",
    title: "Build and run a workflow",
    category: "Advanced",
    summary: "Connect trusted host operations into a validated, deterministic sequence with typed inputs and outputs.",
    outcome: "You can author a small workflow, inspect its execution plan, and run it once in order.",
    beforeStart: ["Become comfortable creating and running a normal prompt first."],
    steps: [
      ["Create a definition", "Choose New workflow and give it a stable id, name, version, and description."],
      ["Define ports", "Add typed workflow inputs and outputs. Port ids identify values passed through the graph."],
      ["Add trusted nodes", "Each node selects an operation from the fixed host catalog and exposes typed ports."],
      ["Connect edges", "Route a workflow input or node output to exactly one compatible destination. Avoid cycles and duplicate targets."],
      ["Save and validate", "Save the definition, then choose Validate and preview plan. Resolve every reported graph issue."],
      ["Supply inputs and run", "Enter run-time values, review the ordered plan, choose Run planned workflow, and confirm."],
    ],
    tips: ["Begin with one node, then add complexity one connection at a time.", "Extensions cannot add unreviewed operations through this UI."],
    related: ["compose-run", "portability", "troubleshooting"],
    keywords: ["workflow", "node", "edge", "port", "graph", "operation", "plan", "sequential", "typed input"],
  },
  {
    id: "portability",
    title: "Import and export safely",
    category: "Manage the app",
    summary: "Move one selected prompt or workflow through a reviewed, bounded JSON file.",
    outcome: "You can transfer individual items without exporting secrets, histories, or hidden application state.",
    beforeStart: ["Open Settings and support.", "Select a saved prompt or workflow before exporting."],
    steps: [
      ["Export one item", "Choose the relevant Download button. The browser saves a portable JSON file for that selected item."],
      ["Choose a destination", "Store the file somewhere you control. Inspect it before sharing if the prompt itself is sensitive."],
      ["Preview an import", "Select a portable JSON file. The application validates and previews it without applying changes."],
      ["Resolve conflicts", "Choose the offered conflict action. Prompt imports target the currently selected existing project."],
      ["Confirm and apply", "Review the destination and conflict choice, check the confirmation box, then apply the import."],
    ],
    tips: ["Portable files never contain provider credentials or extension approvals.", "This is single-item portability, not a complete backup of application data."],
    related: ["settings-support", "privacy-security", "troubleshooting"],
    keywords: ["import", "export", "json", "portable", "conflict", "download", "backup", "transfer"],
  },
  {
    id: "themes-extensions",
    title: "Themes and managed extensions",
    category: "Manage the app",
    summary: "Apply declarative themes and understand the deliberate full-trust boundary for managed extensions.",
    outcome: "You can customize appearance without confusing a theme with trusted executable extension code.",
    beforeStart: ["Open Customize from the workspace header."],
    steps: [
      ["Choose a theme", "Use the theme selector for installed, validated appearance choices. Remember stores the selection as a preference on this device."],
      ["Install a managed theme package", "Only canonical theme packages already provisioned in the app-owned inbox can be reviewed and installed."],
      ["Review an extension", "A managed extension is host code, not a visual theme. Review its exact identity and digest before activation."],
      ["Activate for this session", "Activation requires explicit approval and lasts only for the current application session."],
      ["Restart to reset", "Active extensions return to inactive after restart. Remote discovery and automatic activation are unavailable."],
    ],
    tips: ["Do not approve an extension whose origin or digest you cannot verify.", "A theme changes declared color tokens only; it does not receive extension authority."],
    related: ["privacy-security", "settings-support"],
    keywords: ["theme", "customize", "extension", "plugin", "digest", "activate", "trust", "session", "appearance"],
  },
  {
    id: "settings-support",
    title: "Settings, diagnostics, and support files",
    category: "Manage the app",
    summary: "Manage non-secret preferences and create a reviewed, content-free diagnostic snapshot.",
    outcome: "You can adjust the interface and gather useful support evidence without exporting prompt content or secrets.",
    beforeStart: ["Open Settings and support from the workspace header."],
    steps: [
      ["Set preferences", "Choose compact layout or reduced motion, then save. These non-secret preferences stay on this device."],
      ["Refresh diagnostics", "Review versions, package state, counts, provider availability, and customization status."],
      ["Review support export", "Choose Review support export and inspect the explicit redaction list."],
      ["Download after confirmation", "Confirm only after reviewing what is included and excluded, then download the diagnostic snapshot."],
    ],
    tips: ["Diagnostics exclude prompt content, credentials, paths, and environment values.", "Telemetry and automatic uploads are not enabled."],
    related: ["portability", "troubleshooting", "privacy-security"],
    keywords: ["settings", "compact", "reduced motion", "diagnostics", "support", "redaction", "telemetry", "versions"],
  },
  {
    id: "stress-testing",
    title: "Run a practical stress-test session",
    category: "Testing",
    summary: "Exercise library size, prompt complexity, provider failure handling, workflows, and restarts without risking production data.",
    outcome: "You will collect repeatable observations about speed, stability, recovery, and usability.",
    beforeStart: ["Use a dedicated test project and non-sensitive text.", "Keep portable exports of any test cases you want to repeat."],
    steps: [
      ["Build library volume", "Create prompts in batches and test selection, editing, tags, categories, and project-scoped search as the list grows."],
      ["Increase prompt size", "Add multiple long blocks, reorder and toggle them, save repeatedly, and verify the composed preview remains exact."],
      ["Exercise safe failures", "Try missing required values, invalid workflow edges, cancelled confirmations, and a deliberately unavailable provider credential."],
      ["Repeat workflows", "Run small valid workflows many times and verify step order and final output stay deterministic."],
      ["Test lifecycle", "Close and reopen the app, confirm saved data returns, remembered themes behave as expected, and session-only extensions are inactive."],
      ["Record evidence", "Note the action, item counts, expected result, actual result, elapsed time, and whether restart or data repair was needed."],
    ],
    tips: ["Increase one variable at a time so failures are reproducible.", "Do not use paid provider runs for high-volume testing until local paths are stable."],
    related: ["compose-run", "workflows", "troubleshooting"],
    keywords: ["stress test", "load", "volume", "performance", "repeat", "restart", "failure", "test prompts"],
  },
  {
    id: "troubleshooting",
    title: "Troubleshooting common problems",
    category: "Help",
    summary: "Use visible status messages and safe checks to recover from common setup, save, import, provider, and workflow issues.",
    outcome: "You can identify the failing layer and collect useful diagnostics before asking for support.",
    beforeStart: ["Read the latest status message in the affected area.", "Avoid deleting data as a first troubleshooting step."],
    steps: [
      ["App will not install", "The alpha Windows package is unsigned. Confirm the installer came from the expected build source, inspect its hash, and use your organization’s approved SmartScreen process."],
      ["Library will not open", "Restart once. If the issue remains, open Settings and support and review package and version diagnostics."],
      ["Prompt output looks stale", "Save the prompt again, then create a fresh Compose preview before running."],
      ["OpenAI run fails", "Check credential availability, network access, model selection, account access, and the displayed provider error. The offline provider can isolate composition from connectivity."],
      ["Import is blocked", "Confirm the file is a supported prompt or workflow portable file, within the size limit, and that you selected an existing destination project for a prompt."],
      ["Workflow will not run", "Save it, validate its plan, fix cycles, duplicate targets, type mismatches, or missing values, then confirm the run."],
      ["Prepare support evidence", "Export a reviewed diagnostic snapshot and add your own reproduction steps. The snapshot intentionally omits content and secrets."],
    ],
    tips: ["Copy exact error wording when reporting a problem.", "Include what changed immediately before the issue appeared."],
    related: ["settings-support", "privacy-security", "getting-started"],
    keywords: ["error", "problem", "install", "smartscreen", "save", "stale", "provider failed", "import blocked", "support"],
  },
  {
    id: "privacy-security",
    title: "Privacy, security, and current boundaries",
    category: "Help",
    summary: "Understand what stays local, what can leave the device, and which alpha capabilities are intentionally unavailable.",
    outcome: "You can make an informed decision before entering sensitive material or enabling trusted code.",
    beforeStart: ["Classify the information you plan to place in prompts."],
    steps: [
      ["Local by default", "Projects, prompts, workflows, settings, and managed customization state are stored below per-user Tauri application data."],
      ["External calls are explicit", "Only a confirmed run using an external provider sends the composed prompt and supported options to that provider."],
      ["Secrets use a separate boundary", "The OpenAI credential is protected with Windows DPAPI for the current user and excluded from SQLite, portable files, and diagnostics."],
      ["Extensions are full trust", "Managed extension activation approves exact host code for the current session. Treat it like installing and running software."],
      ["Know the alpha limits", "There is no telemetry, cloud sync, automatic upload, automatic update, remote marketplace, bulk backup, or signed publishing in this checkpoint."],
    ],
    tips: ["Do not enter regulated or confidential data unless your own policy permits both local storage and the selected provider.", "Keep installer and portable-file hashes when provenance matters."],
    related: ["openai-provider", "themes-extensions", "portability"],
    keywords: ["privacy", "security", "local data", "secret", "credential", "telemetry", "cloud", "sensitive", "trust boundary"],
  },
  {
    id: "distribution",
    title: "Install, update, and uninstall the alpha",
    category: "Help",
    summary: "Use the current-user Windows installer with realistic expectations for an unsigned alpha build.",
    outcome: "You can install a verified build and preserve anything important before replacing or removing it.",
    beforeStart: ["Obtain the installer and published SHA-256 from the trusted project build source."],
    steps: [
      ["Verify", "Compare the installer SHA-256 with its acceptance evidence before running it."],
      ["Install", "Run the Windows x64 current-user NSIS installer. Because the alpha is unsigned, Windows may show a SmartScreen warning."],
      ["Launch", "Open Universal Prompt Studio and complete onboarding. Use the offline provider for the first functional check."],
      ["Before replacing or removing", "Export individual prompts and workflows that you need elsewhere. Single-item portability is not a full backup."],
      ["Uninstall", "Use Windows installed-app controls. Treat per-user application data as potentially persistent until you have verified your desired retention or removal outcome."],
    ],
    tips: ["Do not bypass security warnings for an installer whose source or hash you cannot verify.", "Automatic updates and code signing are not part of this alpha checkpoint."],
    related: ["getting-started", "portability", "troubleshooting"],
    keywords: ["install", "installer", "nsis", "windows", "unsigned", "hash", "sha-256", "update", "uninstall", "smartscreen"],
  },
  {
    id: "glossary",
    title: "Plain-language glossary",
    category: "Help",
    summary: "Translate the main Universal Prompt Studio terms into everyday language.",
    outcome: "You can follow the interface and the guide without prior prompt-engineering vocabulary.",
    beforeStart: [],
    steps: [
      ["Project", "A local container that owns a group of prompts."],
      ["Prompt", "A saved set of ordered instruction blocks."],
      ["Compose", "Assemble enabled blocks into the exact final text in their current order."],
      ["Provider", "The controlled execution path that receives a composed prompt, such as Offline reference or OpenAI Responses."],
      ["Workflow", "A saved graph of trusted operations that is validated into a deterministic execution order."],
      ["Portable file", "A reviewed JSON export containing exactly one prompt or workflow."],
      ["Theme", "Declarative appearance tokens that change application colors."],
      ["Managed extension", "Host code with full trust that requires exact, session-only activation approval."],
      ["Diagnostic snapshot", "A content-free support file containing versions, counts, availability, and redaction information."],
    ],
    tips: ["Search Help for any term to see the relevant task guide."],
    related: ["getting-started", "privacy-security"],
    keywords: ["definitions", "terms", "meaning", "project", "prompt", "provider", "workflow", "portable", "diagnostic"],
  },
];

function normalizeText(value) {
  return value.toLocaleLowerCase("en-US").normalize("NFKD").replace(/[\u0300-\u036f]/g, "");
}

function searchableText(topic) {
  return normalizeText([
    topic.title,
    topic.category,
    topic.summary,
    topic.outcome,
    ...topic.beforeStart,
    ...topic.steps.flatMap((step) => Array.isArray(step) ? step : [step.title, step.body]),
    ...topic.tips,
    ...topic.keywords,
  ].join(" "));
}

function freezeTopic(topic) {
  return Object.freeze({
    ...topic,
    beforeStart: Object.freeze([...topic.beforeStart]),
    steps: Object.freeze(topic.steps.map(([title, body]) => Object.freeze({ title, body }))),
    tips: Object.freeze([...topic.tips]),
    related: Object.freeze([...topic.related]),
    keywords: Object.freeze([...topic.keywords]),
  });
}

export const HELP_TOPICS = Object.freeze(rawTopics.map(freezeTopic));
const topicsById = new Map(HELP_TOPICS.map((topic) => [topic.id, topic]));

export function helpTopic(id) {
  return typeof id === "string" ? topicsById.get(id) ?? null : null;
}

export function helpCategories() {
  return Object.freeze([...new Set(HELP_TOPICS.map((topic) => topic.category))]);
}

export function searchHelpTopics(query) {
  if (typeof query !== "string" || !query.trim()) return HELP_TOPICS;
  const terms = [...new Set(normalizeText(query).trim().split(/\s+/).filter(Boolean))];
  return Object.freeze(HELP_TOPICS.filter((topic) => {
    const text = searchableText(topic);
    return terms.every((term) => text.includes(term));
  }));
}
