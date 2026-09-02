# Universal Prompt Studio beginner user guide

This guide is for people who want to build reliable, reusable prompts without
needing to understand the application architecture. It covers the Windows alpha
from installation through everyday use, workflows, portability, diagnostics,
and practical stress testing.

> **Alpha notice:** the current Windows x64 installer is unsigned. Universal
> Prompt Studio has no automatic updater, cloud sync, telemetry, remote
> marketplace, or complete backup/restore feature. Verify the installer source
> and SHA-256 before installation and export important individual prompts or
> workflows before replacing a build.

## 1. What the application does

Universal Prompt Studio stores prompts as ordered blocks rather than one long
text box. You can organize prompts into projects, preview the exact assembled
text, and then run it through either:

- **Offline reference**, a local echo path for checking composition without an
  external AI call; or
- **OpenAI Responses**, a bounded external-provider path that requires a saved
  credential and an explicit confirmed run.

You can also create small sequential workflows from trusted built-in operations,
apply validated themes, review managed extensions, move one prompt or workflow
through a portable JSON file, and export a redacted diagnostic snapshot.

## 2. Install on Windows

### Before installation

1. Obtain the Windows x64 NSIS installer from the project’s trusted build or
   release source.
2. Compare its SHA-256 with the value in the matching acceptance evidence.
3. Do not run an installer whose source or hash you cannot verify.

### Install and launch

1. Run the installer under the Windows account that will use the application.
2. Windows SmartScreen may warn that the publisher is unknown because this
   alpha is not code-signed. Follow your own or your organization’s software
   approval policy. The warning is not proof that an unverified file is safe.
3. Complete the current-user installation.
4. Open **Universal Prompt Studio** from the Start menu or installed shortcut.

The application stores its working data below Tauri-managed per-user application
data. Treat that data as potentially persistent after uninstall unless you have
verified the retention or removal outcome you need.

## 3. First launch

The welcome screen explains three boundaries:

1. Projects own prompts and keep the local library organized.
2. Provider and workflow runs are explicit; nothing runs in the background.
3. Portable imports are reviewed before application and portable exports omit
   credentials, history, and extension approvals.

Read the statements, select the acknowledgement, and choose **Start using the
studio**. You can reopen guidance at any time with **Help** in the workspace
header. The Help dialog is offline, searchable, keyboard accessible, and links
directly from the major product areas.

## 4. The interface at a glance

| Area | Purpose |
| --- | --- |
| Left sidebar | Create and select projects |
| Prompt toolbar | Create and search prompts in the selected project |
| Prompt list | Open a saved prompt |
| Prompt editor | Edit metadata and ordered blocks |
| Preview and run | Compose saved blocks, choose a provider, and run explicitly |
| Workflow studio | Author, validate, plan, and run sequential workflows |
| Customize | Manage themes and session-only extension activation |
| Settings & support | Preferences, import/export, diagnostics, and support files |
| Help | Search the built-in task guide |

## 5. Ten-minute quick start

### Step 1: create a project

In the left sidebar:

1. Enter a project name such as `Product launch`.
2. Optionally add a description.
3. Choose **Create project**.

A project is the local owner of its prompts. Choose a few meaningful groupings,
such as one per client, product, team, or personal area.

### Step 2: create a prompt

1. Select the project.
2. Enter `Draft launch announcement` in the new-prompt title field.
3. Choose **Create prompt**.
4. Add a category such as `Marketing` and tags such as
   `announcement, concise, review`.

### Step 3: build it from blocks

Add and fill these blocks:

| Block | Example |
| --- | --- |
| Role | You are a careful product communications editor. |
| Goal | Draft a clear launch announcement from the supplied facts. |
| Context | The audience already uses the previous version. |
| Constraints | Do not invent features. Keep the response under 250 words. |
| Output format | Return a headline, short introduction, three bullets, and a call to action. |

Keep the blocks enabled and arrange them in the order you want them assembled.
Choose **Save changes**.

### Step 4: preview the exact prompt

Choose **Compose saved prompt**. Read **Final assembled prompt** from top to
bottom. Composition uses the saved, enabled blocks—not unsaved editor changes.
If anything is missing or stale, edit, save, and compose again.

### Step 5: make a safe local run

1. Select **Offline reference** in the provider picker.
2. Choose **Run selected provider**.
3. Read and confirm the run prompt.
4. Verify that the result reflects the composed text.

The offline reference is intentionally simple. It proves that storage,
composition, provider selection, confirmation, and result display work without
contacting an external AI service.

## 6. Build stronger prompts

Each block should answer one question.

| Block type | Question it answers | Practical advice |
| --- | --- | --- |
| Role | What perspective or expertise is needed? | Name capabilities, not a fictional biography. |
| Goal | What single result must be achieved? | Start with an action verb. |
| Context | What background is necessary? | Include only facts that affect the answer. |
| Audience | Who will read or use the result? | State knowledge level, needs, and tone. |
| Constraints | What limits and exclusions apply? | Separate boundaries from required content. |
| Requirements | What details must the result include? | Make mandatory content explicit and testable. |
| Tone | How should the response sound? | Name a practical tone suited to the audience. |
| Output format | What exact structure should be returned? | Name headings, fields, order, and length. |
| Reasoning style | What approach should develop the answer? | Ask for an appropriate approach, not hidden chain-of-thought disclosure. |
| Examples | What does a good pattern look like? | Keep examples small and representative. |
| Validation rules | How will the response be checked? | Use observable acceptance criteria. |
| Final instructions | What last priority must not be missed? | Reserve this for a concise final reminder. |

To debug a weak result, change one block at a time. Disable a block when you
want to test without it but do not want to delete it. Reorder blocks when an
instruction needs to appear earlier or later in the composed prompt.

## 7. Organize and find prompts

- Use a specific, outcome-oriented title: `Summarize customer interview` is
  easier to find than `Useful prompt`.
- Use one category for a broad type of work and a few tags for cross-cutting
  traits such as `legal-review`, `short`, or `research`.
- Search applies to the selected project. Select the correct project before
  deciding an item is missing.
- Save after metadata or block edits. Status text reports whether the operation
  succeeded or failed.
- Deleting a prompt or project requires confirmation and is not a backup
  mechanism. Export important prompts before deleting their project.

## 8. Run with OpenAI Responses

Use this path only when you intend to send the composed prompt to OpenAI and
your data-handling rules allow it.

1. Open a saved prompt and create a fresh composition preview.
2. Select **OpenAI Responses** in the provider picker.
3. Enter the supported model and options shown by the application.
4. Enter an OpenAI API key and save the provider settings.
5. Confirm that the interface reports the credential as available.
6. Choose **Run selected provider** and confirm the external call.
7. Review the response or the safe provider error.

The endpoint is fixed by the host. The credential is protected with Windows
DPAPI for the current Windows user; it is not stored in SQLite, displayed again,
or included in portable and support exports. Use **Clear saved key** when the
credential should no longer remain available to this Windows profile.

API use can incur charges and needs network access. Verify current pricing,
account permissions, model availability, and organizational policy with the
provider before running high-volume tests.

## 9. Create a workflow

A workflow is a typed graph that the application validates into a deterministic
sequential plan. It does not run in the background.

### Build the smallest useful workflow

1. In **Workflow studio**, choose **New workflow**.
2. Enter a stable workflow id, human-readable name, version, and description.
3. Define workflow inputs and outputs. Each port needs a unique id and value
   type.
4. Add a trusted node and select an operation from the fixed host catalog.
5. Connect a workflow input to the node input and the node output to the
   workflow output.
6. Save the definition.
7. Choose **Validate & preview plan**.
8. Correct every reported issue before running.
9. Enter runtime input values, review the exact step order, choose **Run planned
   workflow**, and confirm.

Add complexity one node at a time. Planning rejects unsafe or ambiguous graphs,
including cycles, duplicate targets, missing endpoints, and incompatible types.
Execution performs each planned operation once, in order, and stops safely at a
failing step.

## 10. Import and export

Open **Settings & support** to move one selected item at a time.

### Export

1. Select a saved prompt or workflow in the main interface.
2. Open **Settings & support**.
3. Choose the enabled prompt or workflow download button.
4. Store the JSON file in a location you control.

### Import

1. For a prompt import, first select the existing destination project.
2. Open **Settings & support** and select a supported portable JSON file.
3. Read the preview. No change has been applied yet.
4. Select one of the offered conflict actions.
5. Review the file, destination, and action, then select the acknowledgement.
6. Choose **Apply reviewed import**.

Portable files contain exactly one prompt or one workflow and are bounded to
10,000 Unicode characters. Credentials, run history, settings, diagnostic data,
and extension approvals are excluded. This feature is not bulk backup/restore.

## 11. Themes and extensions

Open **Customize** from the workspace header.

### Themes

Themes are validated declarative color tokens. Select an installed theme from
the header. Choose **Remember** when the preference should survive restart, or
use **Revert** to return to the previous selection. Only canonical theme
packages already provisioned in the app-owned inbox can be reviewed and
installed through the managed package surface.

### Managed extensions

Extensions are different from themes: they are executable host code with full
trust. Activation requires review of an exact identity and digest and lasts only
for the current session. Restarting returns extensions to inactive.

Do not approve an extension unless you trust its origin and have verified its
digest. Remote discovery, requested-permission grants, automatic activation,
and persistent approval are not available in this checkpoint.

## 12. Settings, diagnostics, and support

In **Settings & support** you can:

- enable a compact workspace layout;
- reduce interface motion;
- refresh content-free diagnostics; and
- review and download a redacted support snapshot.

Save preferences after changing them. Diagnostics include versions, package
state, counts, provider availability and credential state, customization counts,
and non-secret settings. They exclude prompt content, credentials, filesystem
paths, and environment values.

Before downloading a support snapshot, choose **Review support export**, read
the redaction list, select the confirmation only if it matches your intention,
and then download. Add your own reproduction steps separately; the diagnostic
file deliberately cannot describe the content that caused a problem.

## 13. Practical prompt recipes

### Summarize source material without invention

- **Role:** careful analyst
- **Goal:** summarize the supplied material
- **Context:** why the summary is needed
- **Constraints:** use only supplied facts; flag missing information
- **Context (source material):** clearly delimited source text
- **Output format:** executive summary, findings, open questions
- **Validation rules:** every claim traceable to the source

### Produce content for a specific audience

- **Role:** subject-matter communicator
- **Goal:** explain one defined topic
- **Audience:** knowledge level, role, needs, and tone
- **Constraints:** word limit, exclusions, terminology rules
- **Examples:** one small representative example
- **Output format:** required headings or channel format
- **Validation rules:** accuracy, clarity, actionability, and format compliance

### Review an existing draft

- **Role:** critical editor
- **Goal:** identify and prioritize improvements
- **Context:** purpose and publication channel
- **Constraints:** preserve verified facts; do not rewrite unless requested
- **Context (draft):** the draft
- **Output format:** issue, impact, recommendation, optional revision
- **Validation rules:** recommendations are specific and evidence-based

## 14. Stress-test plan

Use a dedicated project and non-sensitive test data. Increase one variable at a
time and record the action, item count or size, expected result, actual result,
elapsed time, error wording, and whether a restart was needed.

### Library volume

1. Create 10 prompts, then 50, then larger batches appropriate to your device.
2. Repeatedly select, edit, tag, categorize, save, and search.
3. Check whether list rendering, selection, and search remain responsive.
4. Restart and verify that all successfully saved items return.

### Prompt complexity

1. Add every block type.
2. Increase block length gradually.
3. Reorder, enable, and disable blocks repeatedly.
4. Save and compose after each change.
5. Compare the preview with the expected enabled-block order.

### Safe failure handling

Test missing required fields, cancelled confirmations, invalid portable files,
conflicting imports, absent provider credentials, provider/network errors,
workflow cycles, duplicate destinations, type mismatches, and missing runtime
inputs. The application should report a bounded error and preserve valid saved
state.

### Lifecycle behavior

1. Remember and revert themes.
2. Activate a reviewed managed extension, restart, and confirm it is inactive.
3. Export and re-import representative prompts and workflows.
4. Restart between activity bursts and confirm persisted data.
5. Review diagnostics before and after the run without expecting prompt content
   to appear.

Use the offline provider for high-volume interaction tests. Use paid external
provider calls only for a small, deliberate sample after the local path is
stable.

## 15. Troubleshooting

| Problem | Safe checks |
| --- | --- |
| Installer is blocked | Verify source and SHA-256. The alpha is unsigned, so use only your approved SmartScreen process. |
| Library does not open | Restart once, then review package/version diagnostics. Do not delete app data as a first step. |
| Preview is missing an edit | Save changes, ensure the block is enabled, then compose again. |
| Search finds nothing | Select the correct project, simplify the query, and check title/category/tags. |
| OpenAI is unavailable | Check credential state, network access, account/model access, and the exact displayed error. Use Offline reference to isolate composition. |
| Import is blocked | Confirm the supported file kind and size, select an existing destination project for a prompt, and review the offered conflict actions. |
| Workflow will not plan | Save it and fix every reported endpoint, type, cycle, duplicate-target, or structural issue. |
| Workflow will not run | A valid saved plan, runtime inputs, and explicit confirmation are required. |
| Theme does not persist | Select a managed theme and enable Remember. |
| Extension is inactive after restart | This is expected; activation is intentionally session-only. |

For a useful issue report, include the application version, exact action,
expected result, actual result, exact error wording, reproduction steps, and a
reviewed diagnostic snapshot. Do not paste API keys or confidential prompt
content into an issue.

## 16. Privacy and security boundaries

- Projects, prompts, workflows, preferences, and managed customization state are
  local per-user application data by default.
- A confirmed external-provider run sends the composed prompt and supported
  options to that provider.
- The OpenAI credential is DPAPI-protected for the current Windows user and is
  excluded from SQLite, portable files, and diagnostics.
- Managed extension activation grants exact host code full trust for the current
  session. Treat that decision like running software.
- Telemetry, automatic upload, cloud sync, automatic updates, remote marketplace,
  persistent extension approval, and signed publishing are unavailable.
- The interface and help catalog are currently English-only.

Classify information before entering it. Your organization’s rules may limit
both local storage and which external provider can receive the composed prompt.

## 17. Glossary

| Term | Meaning |
| --- | --- |
| Project | A local container that owns prompts |
| Prompt | A saved record made from ordered instruction blocks |
| Compose | Assemble saved enabled blocks into exact final text |
| Provider | A controlled execution path that receives a composed prompt |
| Offline reference | A local echo provider used to check the application flow |
| Workflow | A typed graph of trusted operations validated into an ordered plan |
| Node | One trusted operation inside a workflow |
| Edge | A connection that routes one typed value to a destination |
| Portable file | A reviewed JSON file containing one prompt or workflow |
| Theme | Declarative color tokens that change appearance |
| Managed extension | Full-trust host code requiring exact session activation |
| Diagnostic snapshot | A content-free, redacted support export |

## 18. What this guide does not promise

This alpha guide documents supported A-001 through A-008 behavior. It does not
promise cloud collaboration, bulk backup/recovery, arbitrary provider endpoints,
background automation, remote extensions, automatic updates, signed packages,
or suitability for regulated production workloads. Those outcomes require
separate requirements, security review, and distribution decisions.
