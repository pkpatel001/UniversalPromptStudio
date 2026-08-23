# ADR-0016: Plugin Package, Installation, and Trust Planning

**Status:** Accepted  
**Milestone:** E-013.4

## Context

E-013.1 through E-013.3 established plugin metadata, discovery, compatibility,
dependencies, and controlled scaffolding. Runtime loading must not begin until
the project has a bounded package format, an explicit installation-location
contract, and a trust decision that cannot be confused with manifest validity.

This checkpoint is intentionally planning-only. It must supply useful security
evidence without extracting packages, persisting trust, installing files, or
executing code.

## Decision

### Canonical package

A UPS Python plugin package is a ZIP named:

```text
<plugin-id>-<plugin-version>.ups-plugin.zip
```

The archive has no enclosing directory. It contains root
`plugin-manifest.yaml`, the manifest entry-point module, and optional safe
source, documentation, and resource files. The manifest remains the identity
authority; the filename must match its ID and version.

`PluginPackageInspector` reads without extraction. It rejects traversal,
absolute and backslash paths, Windows drive syntax, duplicate case-insensitive
paths, non-portable or Windows-reserved names, symlinks, encryption,
unsupported compression, cache/dependency/VCS
directories, secret-bearing paths, missing entry-point modules, and malformed
metadata. Archive, member-count, member-size, total-expanded-size, manifest,
and compression-ratio limits are enforced before and during reads. Every file
and the complete archive receive SHA-256 digests. One bounded byte snapshot is
used for both the archive digest and ZIP inspection so they cannot refer to
different file revisions.

### Trust assessment

Manifest validity, SDK compatibility, dependency satisfaction, and package
integrity are separate from trust. E-013.4 supports only an explicit,
in-memory SHA-256 approval of the exact package bytes. A missing or mismatched
approval blocks readiness.

Hash approval proves only that the inspected bytes match the caller-provided
digest. It does not authenticate a publisher, verify a signature, establish
provenance, review code, grant permissions, or prove safety. No trust decision
is persisted.

### Installation plan

`PluginInstallationPlanner` accepts one explicitly approved, labeled local
root. It plans the canonical target:

```text
<root>/<plugin-id>/<plugin-version>/
```

The root must already exist and must not be a symlink. Existing targets and
installed duplicate identities block readiness; replacement, update, and
removal are not planned. The candidate is combined with structurally valid
installed metadata to evaluate host SDK compatibility, dependency constraints,
and cycles through the existing E-013.2 catalog and resolver.

The result contains the inspected package, hash assessment, portable target,
dependency selections, and deterministic issues. Planning performs no writes.

### CLI

The read-only adapters are:

```powershell
python -m Engineering plugin package inspect PACKAGE
python -m Engineering plugin install plan PACKAGE --approve-sha256 SHA256
```

The second command defaults to the project `Plugins/` root and accepts an
explicit `--root`. There is no install, update, remove, trust-add, or load
command.

## Security boundary

- Archives are never extracted.
- Entry points are never imported, resolved, instantiated, or executed.
- No network, download, dependency installation, or marketplace access occurs.
- No package signature or publisher identity is accepted or verified.
- No trust store or approval state is written.
- No target directories or plugin files are created, replaced, or removed.
- Permission declarations remain metadata and are not grants.

## Consequences

- E-013.5 can review runtime-loading security against an explicit package and
  installation contract.
- Package integrity and installation readiness can be inspected safely today.
- Actual archive creation, extraction, atomic installation, rollback, update,
  removal, signatures, provenance, revocation, remote repositories, and trust
  persistence remain deferred.
