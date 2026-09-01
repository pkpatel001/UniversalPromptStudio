# Desktop UI architecture

The A-005 desktop uses one vertically scrollable workspace with two bounded
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
secondary window, drag canvas, global shortcut, or persisted layout. Theme and
managed extension lifecycle UI remain A-006 scope.
