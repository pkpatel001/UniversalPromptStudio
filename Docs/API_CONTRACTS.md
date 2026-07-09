# API Contracts

The presentation layer should call application services only.

Initial service contracts:

- `ProjectService.create_project`
- `PromptService.create_prompt`
- `PromptService.render_prompt`
- `PromptExecutionService.execute`

Provider and repository contracts are defined under `Backend/interfaces` and `Backend/repositories`.

