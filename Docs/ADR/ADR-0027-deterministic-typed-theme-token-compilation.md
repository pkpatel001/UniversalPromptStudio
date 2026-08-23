# ADR-0027: Deterministic Typed Theme Token Compilation

**Status:** Accepted  
**Milestone:** E-015.4

## Context

E-015.1 through E-015.3 established strict declarative metadata, deterministic
discovery and resolution, and controlled scaffold generation. The next theme
engine boundary must turn one validated palette into stable host-consumable
tokens without prematurely deciding how the frontend selects, persists, or
applies a theme.

Passing arbitrary CSS through the theme SDK would make the metadata reader a
CSS sanitization boundary and weaken the closed schema-1 contract. Directly
modifying frontend files or the DOM would also combine deterministic compilation
with application state and rollback behavior.

## Decision

### Typed compilation

`ThemeTokenCompiler` accepts only a validated `ThemeManifest` and an optional
typed `ThemeAppearance`. When no appearance is supplied it uses the manifest's
declared default. An explicit appearance must have a matching palette; there is
no implicit fallback.

Compilation produces an immutable `ThemeTokenSet` retaining typed theme ID,
version, appearance, and exactly eleven `ThemeToken` values. Token order and
names are a closed host contract:

```text
canvas
surface
surface-muted
text
text-muted
border
primary
primary-text
sidebar
sidebar-text
focus
```

The compiler only maps the corresponding schema-1 `ThemeColor` values. It does
not transform colors, evaluate contrast, resolve assets, or consult ambient
configuration.

### Selector-free serialization

`ThemeCssVariableSerializer` deterministically maps the closed token set to
`--ups-color-*` declarations. It emits no selector, braces, stylesheet, file,
or application instruction. This keeps CSS naming serialization separate from
the later component that owns DOM scope and runtime state.

### CLI

```powershell
python -m Engineering theme tokens MANIFEST [--appearance APPEARANCE]
```

The command reads one exact manifest, prints the identity/version/appearance and
the selector-free declarations, and explicitly reports that no selector or
style application occurred. It performs no writes.

## Security boundary

Token names are fixed by the host and cannot come from manifest text. Token
values are the manifest reader's opaque six-digit hexadecimal colors. Therefore
the compiler cannot introduce arbitrary properties, selectors, URLs, scripts,
commands, asset paths, or credentials.

This is not a CSS sanitizer, accessibility certification, installation step,
or trust decision. It does not modify frontend files, inject CSS, touch the DOM,
persist selection, or apply a theme.

## Consequences

- Theme metadata now has one deterministic typed runtime representation.
- Host integrations can consume a complete, ordered, identity-bound token set.
- Selector ownership and state mutation remain outside the compiler.
- E-015.5 can define controlled theme selection and reversible frontend
  application against this stable token boundary.
- Fonts, icons, assets, custom tokens, contrast enforcement, persistence, live
  preview, and untrusted-theme policy remain deferred.
