# Interfaces

Interfaces are stable extension points. Implementations may change without changing application services or the UI.

Defined contracts include:

- `AIProvider`
- `PromptExecutor`
- `PromptOptimizer`
- `PromptValidator`
- `StorageProvider`
- `TemplateProvider`
- `WorkflowEngine`
- `ExportProvider`
- `Plugin`
- `SearchProvider`
- `EmbeddingProvider`
- `HistoryProvider`
- `SettingsProvider`
- Repository interfaces

`SearchProvider` is consumed through `SearchService`, allowing the application to move from Whoosh to SQLite FTS, FAISS, ChromaDB, Qdrant, Elasticsearch, or semantic search without changing presentation code.
