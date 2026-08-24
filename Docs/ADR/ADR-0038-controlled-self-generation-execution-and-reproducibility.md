# ADR-0038: Controlled self-generation execution and reproducibility verification

**Status:** Accepted
**Milestone:** E-017.2

## Context

E-017.1 defines an immutable allowlisted plan for a new Engineering subsystem,
but deliberately cannot render or write it. The next checkpoint must prove that
the plan can use the established E-009/E-008 pipeline without accepting caller
paths or templates, leaving partial changes, or treating a historical artifact
manifest as sufficient evidence of current reproducibility.

## Decision

Add two fixed E-009 definitions for the same approved subsystem family: the
standard four-artifact scaffold and the same scaffold with its optional passive
CLI adapter. Artifact paths may interpolate only simple declared string
variables. E-008 still resolves and validates every expanded path against the
project boundary before a write.

Add an E-008 in-memory preview operation. It performs normal plan validation,
secret checks, rendering, and destination validation, but never inspects or
writes output files. E-017.2 renders two previews and requires byte-identical
results before execution. Preview artifacts must exactly match the E-017.1 plan
paths, artifact types, and fixed host renderer mapping.

`SelfGenerationService.execute` accepts only the current unchanged ready plan.
It always uses `OverwritePolicy.NEVER`. It delegates rendering and artifact
writes to E-009/E-008, writes the E-009 artifact manifest at the derived package
root, and then verifies:

1. exact current-template bytes for every artifact;
2. manifest template identity, inventory, and SHA-256 hashes;
3. UTF-8 Python parsing and compilation; and
4. an isolated, bytecode-disabled import of the generated package and export.

Every planned destination and the manifest are absent before the transaction.
Any write, manifest, structure, import, or reproducibility failure removes the
new exact files and newly created empty directories. Incomplete rollback fails
distinctly. Existing destinations are never overwritten.

`check` regenerates the approved preview in memory, verifies current files and
manifest, and repeats structure/import checks without rewriting output.
Deterministic issues distinguish missing files, template drift, manifest drift,
hash drift, unsafe symlinks, and invalid Python.

Expose `generate engineering` with normal execution, `--dry-run`, and
`--check`. Dry-run and check are mutually exclusive. No overwrite option is
provided.

## Security boundary

Requests still contain no destination, template ID, command, import path,
credential, or overwrite authority. Path placeholders are simple declared
string fields only; attribute/index access, conversion, formatting, missing
values, and non-string values fail. Expanded traversal and absolute paths remain
subject to E-008 boundary validation.

Generated Python comes exclusively from package-bundled host templates. Import
verification executes that generated host-authored package in-process, so it is
not a sandbox. It disables bytecode writes, uses a private temporary module
namespace, and removes that namespace afterward. Human review of every diff is
still required.

No Git operation, release, publishing action, dependency installation, package
registry, network request, credential lookup, subprocess, arbitrary command,
automatic approval, or security-sensitive core replacement is added.

## Consequences

- The approved subsystem scaffold is reproducible across clean roots.
- Partial artifact and manifest failures are rolled back for the no-overwrite
  self-generation transaction.
- Drift mode checks both historical hashes and outputs expected from current
  approved templates.
- E-017.3 Engineering Toolkit closure and application-development handoff is the
  exact next checkpoint.
