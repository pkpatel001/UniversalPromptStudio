# Settings, portable files, and support

The **Settings & support** button opens the A-007 product controls. This surface
uses only application-owned commands; the webview still has no shell or
filesystem permission.

## First run

On first launch, onboarding explains project-owned prompts, explicit execution,
and reviewed portable files. Completing it records one non-secret local
preference. Telemetry remains disabled and automatic updates remain unavailable.

## Application settings

Two device preferences are available:

- **Compact workspace** reduces layout spacing.
- **Reduce interface motion** removes non-essential animation and transitions.

The complete preference record is saved atomically below per-user application
data. Provider credentials are not part of this record. Provider settings stay
inside the prompt runtime panel, theme selection stays in the main header, and
workflow definitions stay in the workflow studio.

## Export a prompt or workflow

Select a saved prompt or saved workflow, open **Settings & support**, and use its
download action. Each JSON file contains exactly one definition. Prompt exports
do not include the project name. Every export excludes credentials, execution
history, and extension approval.

## Import a portable file

For a prompt, first open the destination project. Choose the JSON file in the
Import & export section. The app validates the complete file and shows its item,
destination conflict, character count, and allowed action before changing
storage. Review the choice and explicitly confirm it.

- **Create** is available when the identity does not exist.
- **Replace** or **Keep existing** is available when the identity already exists
  in the selected destination.
- A prompt identity owned by another project can only be kept; it is never moved
  silently.

The import is bound to the exact preview SHA-256. Editing or replacing the file
after preview prevents apply.

## Diagnostics and support export

Diagnostics show only version/package state and counts for projects, prompts,
workflows, trusted operations, themes, and extensions. They do not contain item
titles or content.

Before a support file can be downloaded, the UI lists every excluded category:
credentials, prompt content, workflow definitions and runtime values, paths,
environment values, extension code, and contributions. The user must acknowledge
that review. The exported file is bound to the preview digest and reports
`contains_credentials: false` and `contains_user_content: false`.

## Deliberate limits

Bulk backup/restore, arbitrary archives or destinations, credential export,
cloud sync, telemetry, automatic upload, and automatic updates are not supported.
The current Windows NSIS package is per-user and unsigned.
