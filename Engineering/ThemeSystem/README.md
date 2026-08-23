# Theme System

E-015.1 defines portable, declarative, non-executing theme metadata. It owns
the exact `theme-manifest.yaml` schema, vendor-qualified identity, canonical
version, Theme SDK API level, default appearance, and semantic color palettes.

Schema 1 recognizes `light`, `dark`, and `high-contrast` appearances. Every
palette contains the same fixed semantic color roles, expressed only as opaque
six-digit hexadecimal values. The default appearance must have a palette and
appearance entries must be unique.

The strict reader rejects missing, unknown, duplicate, malformed, and
secret-like data. Inspection does not load assets, parse or inject CSS, modify
the frontend, or apply a theme.

Fonts, icons, arbitrary/custom tokens, asset paths, contrast scoring,
discovery, compatibility catalogs, scaffold generation, installation,
selection, persistence, and runtime theme application remain later E-015 work.
