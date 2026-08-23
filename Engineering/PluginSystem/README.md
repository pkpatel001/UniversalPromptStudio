# Plugin System

E-013.1 defines the metadata contract for UPS plugins. It safely parses,
validates, discovers, and catalogs exact `plugin-manifest.yaml` files without
importing or executing their entry points.

The subsystem owns plugin identity, restricted canonical PEP 440 versions with
three release components, SDK API-level compatibility, entry-point syntax,
capabilities, permission requests, and plugin dependency constraints.
Capabilities and permissions are metadata only.

Runtime loading, activation, permission enforcement, installation, trust,
signatures, package archives, remote synchronization, and marketplace behavior
are intentionally outside this checkpoint.
