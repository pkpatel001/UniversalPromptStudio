# Database

SQLite is the first supported database target. SQLAlchemy ORM mappings should live under `Backend/infrastructure`.

Business logic must never execute SQL directly. Application services depend on repository contracts from `Backend/repositories/contracts.py`.

## Current SQLite Tables

- `projects`
- `prompts`
- `prompt_blocks`

The SQLite repositories implement `ProjectRepository` and `PromptRepository`. Prompt blocks are stored separately and rehydrated into domain objects in prompt block order.
