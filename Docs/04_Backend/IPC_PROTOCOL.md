# Desktop-to-Python IPC protocol

**Checkpoint:** A-007
**Protocol:** 1
**Storage schema:** 1

## Topology

```text
Vite webview
    -> 37 fixed Tauri commands
        -> Rust BackendManager
            -> declared universal-prompt-studio-backend sidecar
                -> ApplicationIpcRouter
                    -> one SQLite ApplicationContainer
                        -> prompt-library.sqlite3 in Tauri app data
                        -> workflow-definitions.json in Tauri app data
                        -> application-settings.json in Tauri app data
                        -> theme-packages/ managed ingress in Tauri app data
                        -> themes/ active, disabled, and receipt state in Tauri app data
                        -> extensions/ discovery root in Tauri app data
```

Rust resolves Tauri's `app_data_dir`, creates that application-owned directory,
and passes it to the sidecar as `UPS_APP_DATA_DIR` after clearing the inherited
environment. Python appends only the fixed `prompt-library.sqlite3`,
`provider-settings.json`, credential, `workflow-definitions.json`,
`application-settings.json`,
`theme-packages/`, `themes/`, and `extensions/` locations. The webview cannot provide an executable, path, environment value, Python
module, IPC command, arbitrary payload, SQL, or filesystem destination.

The webview retains only `core:default`; it has no shell or filesystem
permission. The database is never placed in the repository, installation
directory, current working directory, or a webview-selected location.

## Transport

Rust lazily starts one long-lived target-triple sidecar. It writes one UTF-8
JSON object per line to stdin and reads one correlated JSON object per line from
stdout. Requests are serialized through one process lock. Rust terminates the
child when the manager is dropped or a transport failure invalidates it.

Messages are limited to 16,384 bytes. Requests and responses reject unknown or
duplicate fields, invalid UTF-8/JSON, non-finite numbers, unsupported protocol
versions, malformed identifiers, uncorrelated responses, and values outside
their command-specific bounds. Responses must arrive within three seconds.

Request envelope:

```json
{
  "schema_version": 1,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "command": "library.prompts.search",
  "payload": {
    "project_id": "76c7169d-9e5d-4db4-bf61-856695d2a91e",
    "query": "installer"
  }
}
```

Success and failure envelopes retain protocol schema 1. Rust allowlists
safe error codes and replaces Python-authored messages with fixed presentation
messages. Unknown errors collapse to `backend.unavailable`.

## Fixed command surface

| Tauri command | Sidecar command | Exact payload | Result |
| --- | --- | --- | --- |
| `backend_readiness` | `application.readiness` | `{}` | Identity, versions, and exact capabilities |
| `library_projects` | `library.projects.list` | `{}` | Up to 50 projects plus `has_more` |
| `library_create_project` | `library.projects.create` | `name`, `description` | Created project |
| `library_delete_project` | `library.projects.delete` | `project_id`, `confirm: true` | Deleted project ID and dependent-prompt count |
| `library_prompts` | `library.prompts.list` | `project_id` | Up to 50 project-owned prompts plus `has_more` |
| `library_create_prompt` | `library.prompts.create` | `project_id`, `title` | Created prompt |
| `library_get_prompt` | `library.prompts.get` | `project_id`, `prompt_id` | One project-owned prompt |
| `library_update_prompt` | `library.prompts.update` | IDs, title, category, tags, blocks | Updated prompt |
| `library_delete_prompt` | `library.prompts.delete` | IDs, `confirm: true` | Deleted prompt ID |
| `library_search_prompts` | `library.prompts.search` | `project_id`, `query` | Up to 50 matching prompts plus `has_more` |
| `library_compose_prompt` | `library.prompts.compose` | `project_id`, `prompt_id` | Owned saved-prompt composition |
| `library_execute_prompt_offline` | `library.prompts.execute-offline` | IDs, `provider_id: ups.offline-echo`, `confirm: true` | Bounded offline result and metadata |
| `provider_catalog` | `providers.catalog` | Empty | Exact two-provider catalog and safe availability state |
| `provider_save_settings` | `providers.settings.save` | Fixed provider/endpoint, model, temperature, output tokens, optional API key | Non-secret provider state only |
| `provider_clear_credential` | `providers.credentials.clear` | Fixed provider, `confirm: true` | Provider state with `missing` credential |
| `library_execute_prompt_configured` | `library.prompts.execute-configured` | IDs, `provider_id: ups.openai-responses`, `confirm: true` | Bounded configured result and metadata |
| `customization_catalog` | `customizations.catalog` | `{}` | Bounded managed theme and extension catalog |
| `theme_install` | `themes.install` | Package filename, exact SHA-256, external-package acknowledgement, `confirm: true` | Applied install or bounded issues |
| `theme_lifecycle` | `themes.lifecycle` | Theme identity/version, `disable` or `restore`, exact SHA-256, lifecycle acknowledgement, `confirm: true` | Applied reversible transition or bounded issues |
| `extension_activate` | `extensions.activate` | Plugin identity/version, exact directory SHA-256, full-trust acknowledgement, `confirm: true` | Session runtime status or bounded issues |
| `extension_deactivate` | `extensions.deactivate` | Plugin identity/version, exact directory SHA-256, `confirm: true` | Inactive runtime status or bounded issues |
| `application_settings` | `application.settings.get` | `{}` | Non-secret preferences plus fixed language/update/telemetry policy |
| `application_settings_save` | `application.settings.save` | Complete three-preference record, `confirm: true` | Atomically saved non-secret preferences |
| `portability_export` | `portability.export` | Item kind/identity and owning project for prompts | One canonical bounded JSON document and digest |
| `portability_preview` | `portability.preview` | Portable document and target project for prompts | Item summary, conflict state, digest, and allowed actions |
| `portability_import` | `portability.import` | Reviewed document/target/digest/action, `confirm: true` | Created, replaced, or skipped result |
| `diagnostics_snapshot` | `diagnostics.snapshot` | `{}` | Content-free version/count/availability states |
| `support_preview` | `diagnostics.support.preview` | `{}` | Included sections, redactions, size, and digest |
| `support_export` | `diagnostics.support.export` | Reviewed digest, redaction acknowledgement, `confirm: true` | Canonical redacted support document |
| `workflow_operations` | `workflows.operations.list` | `{}` | Exact trusted operation catalog |
| `workflows` | `workflows.list` | `{}` | Up to 50 deterministic workflow summaries |
| `workflow_create` | `workflows.create` | One exact schema-1 workflow definition | Created definition |
| `workflow_get` | `workflows.get` | `workflow_id` | One exact schema-1 definition |
| `workflow_update` | `workflows.update` | Immutable `workflow_id` plus exact definition | Updated definition |
| `workflow_delete` | `workflows.delete` | `workflow_id`, `confirm: true` | Deleted workflow ID |
| `workflow_plan` | `workflows.plan` | `workflow_id` | Valid ordered plan or bounded failures |
| `workflow_execute` | `workflows.execute` | Workflow/run IDs, typed inputs, `confirm: true` | Bounded sequential steps and outcome |

Readiness returns these commands in the table's exact sidecar-command order.
Application, protocol, and storage versions remain `0.2.0-alpha`, `1`, and `1`.

## Value bounds and prompt shape

| Value | Accepted bound |
| --- | --- |
| Project name | 1–120 trimmed characters |
| Project description | 0–1,000 trimmed characters |
| Prompt title | 1–120 trimmed characters |
| Category | null or 1–80 trimmed characters; empty normalizes to null |
| Tags | Up to 10 unique case-insensitive single-line values, each 1–32 characters |
| Blocks | Up to 12 in array order |
| Block content | 1–2,000 trimmed characters; 12,000 total characters |
| Search query | 1–120 trimmed characters |
| Final composed prompt | 1–12,500 characters |
| Offline execution output | 1–12,564 characters |
| Provider catalog | Exactly two host-owned entries in fixed order |
| Provider endpoint | Exactly `https://api.openai.com/v1/responses` |
| Provider model | 1–80 characters in the host-owned identifier grammar |
| Temperature | Finite number from 0 through 2 |
| Maximum output tokens | Integer from 1 through 4,096 |
| Credential ingress | 8–512 non-control characters; never returned |
| Configured execution output | 1–12,500 characters |
| Collections | First 50 deterministic results plus `has_more` |
| Customization catalog | Up to 20 themes, 20 extensions, and 10 bounded issues |
| Theme or extension identity | Canonical qualified ID up to 128 characters |
| Theme or extension version | Stable numeric `major.minor.patch` without leading zeroes |
| Package or directory digest | Exactly 64 lowercase hexadecimal SHA-256 characters |
| Theme tokens | Exact fixed semantic token names and bounded validated values |
| Workflow definitions | Up to 50 exact schema-1 records; 12,000 encoded bytes each |
| Workflow boundary ports | Up to 8 inputs and 8 outputs |
| Workflow graph | 1–8 nodes and up to 64 edges |
| Workflow operations | Exact three-entry host registry; node ports must match the selected contract |
| Workflow runtime string | Up to 1,000 characters |
| Workflow runtime value | JSON-shaped, non-null, and up to 6,000 encoded bytes |
| Portable document | One prompt or workflow; 1–10,000 Unicode characters |
| Portable response | Up to 14,000 encoded bytes inside the 16 KiB transport |
| Application settings | Exact three booleans in an atomic schema-1 document up to 4 KiB |
| Support document | Counts/states only; up to 12,500 characters at the Rust/webview gate |

Prompt results contain exact `prompt_id`, `project_id`, `title`, nullable
`category`, sorted `tags`, ordered `blocks`, `created_at`, and `updated_at`
fields. A block contains exact `block_type`, `content`, zero-based contiguous
`order`, and `enabled` fields. Block types are limited to the domain-owned
`PromptBlockType` enumeration. IDs are canonical lowercase UUID strings and
timestamps are UTC.

The frontend submits `blockType` to Tauri. Rust deserializes that camelCase
field and deliberately serializes it as `block_type` to the sidecar. Rust then
validates the snake_case response independently before returning camelCase to
the webview.

## Management semantics

- Prompt detail, update, delete, and search always require an owning project ID.
- A prompt ID from another project is indistinguishable from a missing prompt.
- Updates replace the editable title, category, tags, and ordered blocks and set
  a new durable UTC `updated_at` value while preserving identity and creation.
- Search is a deterministic case-insensitive substring scan across title,
  category, tags, and block content, restricted to one selected project and
  returned in repository title/identifier order.
- Prompt deletion requires `confirm: true` and removes only the owned prompt.
- Project deletion requires `confirm: true` and removes the project plus all
  dependent prompts in one SQLite repository transaction. The response reports
  the dependent-prompt count.
- There is no arbitrary filter, sort, SQL, path, background index, fuzzy search,
  cross-project search, recycle bin, or automatic recovery.

## Composition and execution semantics

- Compose and execute always reload one prompt through its owning project ID;
  the webview cannot submit arbitrary prompt text for execution.
- `PromptBuilder` renders only enabled, non-empty blocks in stored order. Each
  section uses the domain block-type heading followed by trimmed saved content,
  with sections separated by one blank line.
- Composition returns the project/prompt IDs, saved title, final prompt, enabled
  and total block counts, and Unicode character count. It does not change SQLite.
- Offline execution still requires exact `ups.offline-echo` and `confirm: true`.
- The provider catalog returns only offline echo and `ups.openai-responses`,
  including fixed descriptive metadata, bounded non-secret settings, one opaque
  credential reference, and `missing`, `stored`, or `not-required` state.
- Provider-settings save accepts only `ups.openai-responses`, the fixed endpoint,
  the closed model/temperature/output-token fields, and an optional API key. The
  response never contains the API key. A null credential retains an existing key.
- Credential clearing requires exact provider identity and `confirm: true`.
- Configured execution requires exact `ups.openai-responses` and `confirm: true`.
  The webview cannot send endpoint, model, options, credential, or final prompt
  through the execution command.
- Execution recomposes current durable state rather than accepting or trusting a
  prior webview preview. The returned result contains only project/prompt IDs,
  provider ID/version, a correlated execution UUID, output, input/output units,
  composed prompt character count, and—only for configured execution—the
  validated response model.
- Composition, execution output, and execution metadata are ephemeral. They are
  not written to schema 1, history storage, the installation, or the repository.
- Provider failures map to the fixed `execution.failed` presentation error;
  provider-authored detail and Python exceptions do not cross Rust.

There is no arbitrary provider selection, endpoint, header, credential reference,
option name, model discovery, dynamic provider loading, streaming, cancellation,
retry, background execution, or history persistence.

## Customization lifecycle semantics

- Catalog discovery uses only the fixed application-data roots. The webview
  cannot supply or enumerate a path.
- Built-in themes remain host-owned. Managed selections are compiled only from
  active packages whose exact managed receipts and package digests validate.
  Any managed-theme integrity issue suppresses every dynamic selection.
- External theme install accepts only one canonical package filename already in
  `theme-packages/`, blocks the reserved `ups.*` namespace, rechecks the exact
  approved SHA-256, and requires both acknowledgement and confirmation.
- Disable and restore use the existing managed holding area. Neither transition
  deletes, overwrites, repairs, or trusts changed package bytes.
- Permission-requesting plugins are blocked. A permissionless plugin can run
  only after its current directory digest matches the approved digest and the
  user explicitly acknowledges full in-process trust and confirms activation.
- Extension approval and contributions are process-local. Restart returns every
  extension to `inactive`; runtime approval is never persisted.
- There is no arbitrary CSS or asset application, extension install/remove/
  update, permission grant, dynamic command, marketplace, remote discovery,
  automatic download/update, signature trust, or silent activation.
## Product settings, portability, and support semantics

- `application-settings.json` stores only onboarding completion, compact layout,
  and reduced motion. Language is fixed to English, telemetry is disabled, and
  automatic updates are unsupported. Invalid storage is left unchanged.
- Portable exports contain exactly one selected prompt or workflow. The webview
  receives content and a safe filename, never a path or filesystem capability.
- Prompt export excludes its project name. Every portable file excludes
  credentials, execution history, and extension approval.
- Import validates and previews the exact document before apply. The preview
  reports conflict state and allowed create/replace/skip choices. Apply requires
  the same SHA-256, an allowed explicit choice, and confirmation.
- A prompt identity owned by another project cannot be moved or replaced; only
  skip is allowed. Workflow conflicts are similarly explicit.
- Diagnostics contain versions, package state, counts, provider availability/
  credential state, customization counts, and non-secret preferences only.
- Support preview lists included sections and all fixed redactions. Export
  requires the reviewed digest, redaction acknowledgement, and confirmation.
- Support data excludes credentials, prompt content, workflow definitions and
  runtime values, paths, environment values, extension code, and contributions.
- There is no bulk archive, arbitrary path, cloud sync, telemetry, automatic
  upload/update, credential export, silent resolution, or unreviewed collection.

## Workflow authoring and execution semantics

- Definitions use only the passive Workflow SDK schema-1 identity, boundary
  ports, nodes, trusted operation IDs, and directed edges.
- The operation catalog is exactly `ups.echo-text`,
  `ups.execute-saved-prompt`, and `ups.uppercase-text`. Node ports must equal the
  resolved host operation contract.
- Drafts that satisfy structural and trusted-operation bounds may be saved even
  when their graph is not executable. Planning reports bounded graph failures
  without changing the definition.
- A current saved definition must produce a valid deterministic plan before the
  execution command accepts it. Execution requires a canonical run UUID and
  exact `confirm: true`.
- The saved-prompt node accepts only project, prompt, and authorized provider
  identities. It reloads current durable prompt and provider state and accepts
  no arbitrary prompt text, endpoint, option, or credential.
- Each planned operation runs once in topological order. Intermediate and final
  values are bounded, returned to the caller, and never persisted.
- There are no dynamic handlers, arbitrary operation IDs, cycles, conditions,
  parallelism, retries, cancellation, background scheduling, resume, run
  history, sync, or remote triggers.

## SQLite lifecycle

A-007 retains schema version 1 because provider settings, workflow
definitions, theme receipts, and extension runtime state are not prompt-library
records. A-002.1 already persisted project
ownership, categories, tags, ordered blocks, and update timestamps. No database
shape change or migration is needed, and existing schema-1 user data is opened
unchanged.

Non-secret provider settings use bounded atomic schema-1 JSON below app data.
The fixed credential reference resolves to a current-user Windows DPAPI blob.
Workflow definitions use a separate bounded, exact-shape, atomic schema-1 JSON
document. Invalid workflow storage fails without deletion, replacement,
truncation, rename, downgrade, or automatic repair. Managed theme receipts and
disabled packages remain under the fixed theme root. Application preferences use a
separate exact-shape atomic schema-1 JSON document; extension approval is not
stored.

Fresh databases still follow the owned migration from version 0 to 1. Every
connection enables foreign keys, modern transaction control, trusted-schema
protection, and a bounded busy timeout. Startup validates integrity, tables,
columns, and relationships. Future, corrupt, unmanaged, incomplete,
relationship-invalid, and unavailable databases fail without deletion,
replacement, rename, truncation, downgrade, or automatic repair.

## Lifecycle and trust boundary

- Development and release builds use the same frozen executable; there is no
  system-Python or checkout fallback.
- Transport, timeout, malformed response, or process failure discards the child;
  invalid input and not-found results keep a healthy process.
- Source, frozen-sidecar, restart, and installed-layout tests prove management,
  composition, both provider states, DPAPI ciphertext/redaction, workflow
  persistence/planning/execution, managed-theme install/disable/restore, application-settings restart, reviewed
  prompt/workflow portability, redacted support export, extension restart reset,
  and offline execution while durable storage remains
  under per-user app data.
- The sidecar exposes only two host-created providers. The OpenAI provider makes
  one explicitly initiated HTTPS POST to the fixed endpoint, resolves only its
  fixed DPAPI credential reference, performs no automatic retry, and returns no
  raw transport error. The protocol exposes no arbitrary network operation,
  arbitrary workflow handler, arbitrary customization path, plugin permission,
  dynamic command, filesystem access, or subprocess launch.

The sidecar remains trusted application code with the user's process authority;
this protocol is an authority-reduction boundary, not a sandbox.

Primary guidance:

- <https://docs.rs/tauri/latest/tauri/path/struct.PathResolver.html>
- <https://v2.tauri.app/develop/sidecar/>
- <https://v2.tauri.app/security/capabilities/>
- <https://www.sqlite.org/pragma.html>
- <https://docs.sqlalchemy.org/en/20/dialects/sqlite.html>
