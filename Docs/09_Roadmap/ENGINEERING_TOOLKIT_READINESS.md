# Engineering Toolkit readiness

**Milestone:** E-017.3
**Recommendation:** Close the Engineering Toolkit phase and begin application
vertical slices. Retain version `0.2.0-alpha`.

## Recommendation

The toolkit is stable enough to support product development: its contracts are
typed and deterministic, passive boundaries are side-effect free, controlled
execution paths are explicit, and the Python/frontend/Rust validation matrix is
green. The repository is not beta-ready because the frontend has no production
IPC connection to the Python application composition root and key user-facing
workflows remain unimplemented.

Keep `0.2.0-alpha` aligned across Python, npm, and Cargo for this closure. A
version bump would imply a distributable product increment that E-017.3 does
not deliver. Reconsider `0.3.0-alpha` after the first usable application slice;
reserve beta for a tested desktop flow with persistence, IPC, failure handling,
and packaging evidence.

## Closure gates

E-017.3 requires fresh evidence for:

- the complete Python test suite;
- manifest validation and migration planning;
- generated theme and self-generation drift checks;
- frontend tests and production build;
- locked Rust compilation;
- Python sdist/wheel construction without dependency installation;
- E-010 build planning/execution and manifest evidence;
- E-011 release preconditions, dry-run, and independent existing package-set
  verification; and
- exact diff and accidental-artifact review.

The completion report for the checkpoint records the live counts and outcomes.
Historical counts in earlier handoffs are not acceptance evidence.

## Release posture

Local release packaging is supported. Publishing, signing, tagging, GitHub
Release creation, registry access, and dependency installation are not part of
closure. Existing release output must be verified or explicitly replaced; the
default no-overwrite refusal is expected safety behavior.
