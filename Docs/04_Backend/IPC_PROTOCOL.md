# Desktop-to-Python IPC protocol

**Checkpoint:** A-002.2
**Protocol:** 1
**Storage schema:** 1

## Topology

```text
Vite webview
    -> ten fixed Tauri commands
        -> Rust BackendManager
            -> declared universal-prompt-studio-backend sidecar
                -> ApplicationIpcRouter
                    -> one SQLite ApplicationContainer
                        -> prompt-library.sqlite3 in Tauri app data
```

Rust resolves Tauri's `app_data_dir`, creates that application-owned directory,
and passes it to the sidecar as `UPS_APP_DATA_DIR` after clearing the inherited
environment. Python appends only the fixed `prompt-library.sqlite3` filename.
The webview cannot provide an executable, path, environment value, Python
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

Success and failure envelopes retain the exact A-002.1 schema. Rust allowlists
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
| Collections | First 50 deterministic results plus `has_more` |

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

## SQLite lifecycle

A-002.2 retains schema version 1 because A-002.1 already persisted project
ownership, categories, tags, ordered blocks, and update timestamps. No database
shape change or migration is needed, and existing schema-1 user data is opened
unchanged.

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
- Source, frozen-sidecar, restart, and installed-layout tests prove edits,
  organization, search, and deletion while storage remains under per-user app
  data.
- The sidecar performs no prompt execution, provider request, credential access,
  workflow execution, network access, arbitrary filesystem access, or subprocess
  launch through this protocol.

The sidecar remains trusted application code with the user's process authority;
this protocol is an authority-reduction boundary, not a sandbox.

Primary guidance:

- <https://docs.rs/tauri/latest/tauri/path/struct.PathResolver.html>
- <https://v2.tauri.app/develop/sidecar/>
- <https://v2.tauri.app/security/capabilities/>
- <https://www.sqlite.org/pragma.html>
- <https://docs.sqlalchemy.org/en/20/dialects/sqlite.html>
