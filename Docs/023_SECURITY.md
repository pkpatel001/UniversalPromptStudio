# Security

## Trusted plugin runtime

E-013.5 provides an explicit project-local Python plugin runtime. It is a
full-trust in-process design selected to finish the Engineering Toolkit quickly
while retaining a replaceable loader boundary.

Before code is imported, the host:

- validates plugin metadata, SDK compatibility, and dependencies;
- rejects symlinked, unsafe, ambiguous, excluded, or oversized directory
  content;
- captures one bounded immutable snapshot used for both SHA-256 approval and
  Python source loading;
- confirms the snapshot manifest equals the validated manifest;
- requires an exact ephemeral directory SHA-256 approval;
- requires an explicit full-trust acknowledgment; and
- blocks every plugin with a non-empty permission request.

Activation uses a manifest-capability-scoped registration context. Contributions
commit only after activation succeeds. Failure discards staged contributions and
removes the private module namespace. Deactivation clears host-owned
contributions and module state even when plugin cleanup fails. Loaded and
unloaded events are emitted only after successful lifecycle transitions.

This is not a security sandbox. Plugin code runs with the same process,
filesystem, network, environment, credential, and operating-system authority as
Universal Prompt Studio. A matching digest proves exact approved bytes only; it
does not authenticate a publisher, establish provenance, review code, or make
code safe. Do not activate code you do not fully trust.

There is no automatic startup loading, persisted approval, marketplace or remote
loading, package extraction or installation, permission enforcement, signature
verification, revocation, subprocess boundary, or OS sandbox.

## Deferred security areas

- process or OS isolation for untrusted plugins;
- enforceable plugin permissions;
- package signatures, publisher identity, provenance, and revocation;
- encryption;
- secret and credential storage; and
- future cloud-provider security.
