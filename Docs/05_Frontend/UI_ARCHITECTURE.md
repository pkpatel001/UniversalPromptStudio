# Desktop UI architecture

The A-008 desktop uses one vertically scrollable workspace with bounded
product surfaces. It has no router, hidden administrative screen, shell panel,
or filesystem browser.

## Prompt library

The existing library surface opens automatically. Its project browser controls
project creation, selection, and confirmed deletion. The prompt browser is
scoped to the selected project and provides creation, search, selection, and
confirmed deletion. The editor owns title, category, tags, ordered typed blocks,
composition preview, provider selection/settings, credential availability, and
explicit execution. Status and output panels show bounded presentation-safe
results.

## Workflow studio

The workflow studio is appended to the same workspace and contains:

- a local workflow browser and create action;
- metadata and typed workflow input/output editors;
- an ordered node presentation with operation choices from the trusted catalog;
- a directed-edge editor whose options are derived from current ports;
- deterministic plan or graph-failure presentation;
- provider/project/prompt-aware runtime fields for the saved-prompt operation;
- explicit confirmed sequential execution; and
- pending step, completed step/intermediate output, and final outcome panels.

Save persists a schema-1 definition below application data. Validate always
plans the saved definition. Run remains disabled until that plan is valid.
Changing a draft clears the displayed plan, preventing execution of a stale
preview.

## Navigation and window behavior

The app has one native Tauri window and uses normal document tab order, native
form controls, status live regions, buttons, and scroll. There is no docking,
secondary window, drag canvas, global shortcut, or arbitrary persisted layout.

## Settings, onboarding, portability, and support

A native modal product hub owns non-secret compact-layout and reduced-motion
preferences, selected prompt/workflow export, reviewed import conflict handling,
redacted diagnostics, and digest-bound support export. A separate first-run dialog
explains local storage and explicit execution before recording onboarding
completion. Native dialog focus/Escape behavior, normal tab order, live status
regions, responsive single-column layouts, and reduced-motion overrides are used.
The file input and Blob download stay inside the browser surface; Tauri receives
content, never a filesystem path.
## Help and learning

A native modal Help surface renders a fixed host-authored catalog of 15 offline
topics. Search is deterministic, case-insensitive, and local; it indexes only the
authored titles, summaries, steps, tips, and keywords. Results and article
content are built with text nodes rather than arbitrary HTML.

The workspace header opens the beginner quick start. Contextual buttons open
task-specific guidance from prompt blocks, composition and provider execution,
workflows, managed customization, portability, and settings/support. Related
topic buttons keep navigation inside the same catalog. The dialog uses native
focus/Escape behavior, a live result count, responsive one-column fallback, and
the current semantic theme tokens. It adds no IPC command, network request,
filesystem permission, web storage, or extension authority.

The matching long-form manual is Docs/05_Frontend/USER_GUIDE.md.
