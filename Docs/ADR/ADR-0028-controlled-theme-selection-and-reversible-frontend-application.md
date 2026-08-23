# ADR-0028: Controlled Theme Selection and Reversible Frontend Application

**Status:** Accepted  
**Milestone:** E-015.5

## Context

E-015.4 established a fixed, typed set of eleven semantic tokens and a
selector-free serialization boundary. Universal Prompt Studio now needs visible
theme selection without allowing theme metadata to inject arbitrary CSS or
combining session application with persistence, installation, or startup policy.

The current frontend is deliberately small and dependency-free. Adding a state
framework, CSS-in-JS system, or Tauri command solely for theme switching would
increase the application surface without improving the trust boundary.

## Decision

### Selection payload

The frontend accepts an exact object containing `themeId`, `version`,
`appearance`, and `tokens`. It independently validates vendor-qualified
identity, major.minor.patch version shape, recognized appearance, all eleven
fixed token names, no unknown fields, and opaque six-digit hexadecimal values.

E-015.5 exposes only host-authored `ups.built-in` light, dark, and high-contrast
selections. It does not transport discovered manifests into the frontend or
grant installed themes runtime authority.

### Application controller

`ThemeApplicationController` receives an explicit DOM style root. It maps the
closed token set to the corresponding `--ups-color-*` custom properties and
sets three bounded identity attributes. It never accepts a selector or property
name from the selection.

Validation completes before mutation. Before each application the controller
captures the current property values, priorities, and bounded attributes. If a
write fails, that snapshot is restored and the prior active selection remains.

The first successful application also captures the original baseline. Later
theme switches do not replace it. Explicit revert restores the baseline exactly
and clears the controller state. A failed revert restores the complete active
snapshot. Revert with no active theme is idempotent.

### User interface and lifecycle

The application header provides an explicit selector and revert control with a
live status message. No theme is applied automatically. Selection is not stored;
refresh or restart returns to the stylesheet defaults.

The existing stylesheet defines the same eleven default variables and consumes
them for canvas, surfaces, text, borders, primary actions, sidebar, and focus.
No Tauri command, permission, capability, filesystem access, or network access
is added. The desktop packaging gate runs the dependency-free frontend tests
before its npm audit and full build.

## Security boundary

The controller uses `style.setProperty` with host-fixed names. It does not use
`cssText`, create style elements, accept CSS rules, modify HTML, load assets, or
evaluate code. Invalid selections produce no writes. Application failure is
bounded by rollback and does not silently replace the active selection.

This boundary does not authenticate external themes, evaluate contrast, claim
accessibility conformance, or make arbitrary manifest content safe to apply.

## Consequences

- Users can explicitly switch among three host-authored appearances and return
  to the exact original application colors.
- Theme switching is deterministic, testable, atomic, and dependency-free.
- The frontend now consumes the E-015.4 naming contract without accepting
  arbitrary CSS.
- A later checkpoint can define a controlled catalog-to-frontend transport and
  opt-in preference persistence separately.
- External theme installation, provenance, startup activation, live preview,
  asset handling, and untrusted-theme policy remain deferred.
