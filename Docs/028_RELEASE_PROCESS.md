# Release process

Universal Prompt Studio remains at `0.2.0-alpha`. The E-011 Release System
creates and independently verifies local packages; it does not publish them.

## Local readiness

```powershell
python -m pytest -q
python -m Engineering manifest validate
python -m Engineering theme sync-frontend --root Themes --check
python -m Engineering build run
python -m Engineering release plan
python -m Engineering release run --dry-run
```

The Git working tree must be clean and Python, npm, and Cargo metadata versions
must agree. An existing non-empty `release/` directory is rejected unless
`--overwrite` is explicit.

## Local packaging

```powershell
python -m Engineering release run
python -m Engineering release verify
```

The package set contains a Python source distribution, wheel, deterministic
frontend ZIP, unsigned Windows NSIS installer, `SHA256SUMS`, and
`release-manifest.json`. `release verify` independently checks manifest
coverage, safe archive contents, sizes, formats, and SHA-256 values.

`Scripts/package-desktop.ps1` is the complete local/CI acceptance entry point.
It may install only locked frontend dependencies as part of an explicitly
requested package build. E-017.3 closure does not install dependencies or
contact package registries.

## Version recommendation

Keep `0.2.0-alpha` through Engineering Toolkit closure. Consider
`0.3.0-alpha` after the first usable application vertical slice. Beta requires
a tested frontend/backend IPC path, persistence, failure handling, and current
packaging evidence.

## Deferred release authority

Signing, publishing, registry uploads, Git tags, GitHub Releases, MSI packages,
and updater metadata require a separate reviewed product checkpoint. No
Engineering command performs them automatically.
