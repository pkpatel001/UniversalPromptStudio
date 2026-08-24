# Engineering Toolkit capability matrix

**As of:** E-017.3 closure

“Supported” means implemented, documented, and covered by repository tests. It
does not imply that every capability is exposed in the desktop UI.

| Area | Supported now | Deferred / unsupported |
| --- | --- | --- |
| Core engineering | Canonical paths, typed configuration, standards validation, diagnostics, deterministic documentation | Remote configuration, autonomous repair |
| Code generation | Registered renderers, normalized relative destinations, dry-run, conflict policy, secret checks, rollback | Arbitrary executable templates, unrestricted destinations |
| Templates | Versioned definitions, catalog resolution, controlled variables, artifact manifests | Remote template registry, automatic approval |
| Build | Backend, frontend, and full deterministic validation profiles; build manifest | Cross-platform binary matrix in the local orchestrator |
| Release | Local sdist, wheel, frontend ZIP, unsigned Windows NSIS packaging; checksums and independent verification | Publishing, signing, Git tags/releases, MSI, updater metadata |
| Manifests | Passive discovery for build, documentation, release, template artifact, plugin, provider, theme, and workflow families; compatibility and migration planning | Automatic migration application, remote schemas |
| Plugins | Strict metadata, deterministic catalog/dependencies, scaffold, package inspection/install planning, exact-SHA trusted local runtime | Sandbox, permission enforcement, extraction/install, signatures, trust persistence, updates, marketplace |
| AI providers | Strict metadata/catalog, scaffold, explicit runtime registration, controlled text invocation, offline reference adapter | External loading, credentials/endpoints, model discovery, streaming, cancellation, retries, health checks |
| Themes | Strict declarative palettes, scaffold, token compilation, frontend catalog, apply/revert, preference, exact-SHA managed install/disable/restore | Fonts/assets/icons, arbitrary CSS/tokens, signatures, updates, remote marketplace, automated contrast audit |
| Workflows | Strict schema-1 DAG, catalog/graph validation, scaffold, deterministic planning, explicit handlers, bounded sequential offline execution | Visual editor, cycles, conditions, parallelism, retries, persistence, scheduling, external handlers |
| Self-generation | One allowlisted Engineering subsystem scaffold, optional passive CLI adapter, no-overwrite transaction, manifest and drift verification | Autonomous rewriting, arbitrary paths/templates/commands, automatic Git or release operations |
| Desktop product | Tauri/Vite shell, theme selection, Python composition root, offline references, bounded development readiness IPC | Bundled Python runtime/sidecar, complete prompt library/composer, workflow UI, provider settings, distribution polish |

## Trust summary

- Declarative manifests are data, never import instructions.
- Discovery roots are explicit and symlink-safe.
- Exact SHA-256 approval proves byte identity, not publisher identity or safety.
- In-process plugins and host-created handlers have full process authority.
- No toolkit command automatically commits, pushes, tags, publishes, installs
  dependencies, or contacts a provider.
