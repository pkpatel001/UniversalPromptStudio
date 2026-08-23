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

E-015.2 adds deterministic exact-filename discovery below explicitly approved
roots, stable root provenance, duplicate identity rejection, Theme SDK API-level
compatibility, and an in-memory catalog that resolves exact or highest versions
with optional required appearances. Root order never establishes precedence.

E-015.3 adds controlled project-local scaffold generation through the shared
E-009 template and E-008 generation pipeline. A scaffold is restricted to one
direct child of `Themes/` and contains only `theme-manifest.yaml`, `README.md`,
and the generated `.ups-artifact-manifest.json`. Built-in light, dark, and
high-contrast palettes provide deterministic starting values; generation never
applies them.

E-015.4 compiles one validated palette into an immutable set of exactly eleven
host-recognized semantic tokens. The selector-free serializer maps only those
fixed names to `--ups-color-*` declarations and preserves already-validated
opaque hexadecimal values. Compilation defaults to the manifest appearance or
requires an explicitly declared appearance; it performs no writes or style
application.

E-015.5 adds a dependency-free frontend application controller for the same
closed token set. Host-authored light, dark, and high-contrast selections are
applied only after an explicit session action. Theme replacement is atomic,
failed writes restore the previously active values, and revert restores the
exact pre-theme properties, priorities, and selection attributes.

E-015.6 compiles compatible palettes from explicit theme roots into one
deterministic generated frontend module. The module is independently validated
before use, and desktop packaging rejects drift. Users may explicitly remember
a selection; storage contains only schema version, theme ID, theme version, and
appearance. Tokens are always resolved from the current transported catalog.

E-015.7 defines a canonical data-only external package containing exactly one
root manifest. Inspection hashes one bounded archive snapshot without extraction.
Installation requires both an exact SHA-256 and explicit external-theme
acknowledgement, derives a managed project-local target, refuses replacement,
and atomically writes the inspected manifest with a deterministic provenance
receipt. Installation neither synchronizes the frontend catalog nor activates a
theme.

Fonts, icons, arbitrary/custom tokens, asset paths, contrast scoring, signatures,
authenticated publishers, updates, removal, revocation, live preview, and asset
handling remain later work.
