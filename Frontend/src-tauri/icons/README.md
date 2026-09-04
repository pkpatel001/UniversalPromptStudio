# Application icon assets

The Windows icon set is derived from the simplified Universal Prompt Studio
mark approved on 2026-09-04.

## Sources

- `app-icon-approved-reference.png` preserves the approved generated concept.
- `app-icon.svg` is the flat production vector master used from 128 px upward.
- `app-icon-small.svg` is the adaptive small-size master. It removes the node
  detail and strengthens the primary shapes for 16–64 px rendering.

The production palette is deep blue `#0b4778`, technology blue `#1688db`, and
amber `#f59e0b`. Both vector sources use transparent outer backgrounds, flat
fills, and generous safe margins.

## Windows outputs

The root folder contains adaptive PNGs at 16, 20, 24, 32, 40, 48, and 64 px;
standard Tauri PNGs at 128 and 256 px; a 512 px `icon.png`; the Windows Store
square-logo family; and `icon.ico` with embedded 16, 24, 32, 48, 64, and 256 px
frames.

`tauri.conf.json` consumes `32x32.png`, `128x128.png`, `128x128@2x.png`, and
`icon.ico` for the current NSIS desktop package.

## Regeneration

Run these commands from `Frontend` into a staging directory:

```powershell
npx tauri icon src-tauri/icons/app-icon.svg --output ../build/icon-staging/main
npx tauri icon src-tauri/icons/app-icon-small.svg --output ../build/icon-staging/small --png 16 --png 20 --png 24 --png 32 --png 40 --png 48 --png 64
```

Copy the 128 px, 256 px, 512 px, ICO, and Windows Store outputs from `main`.
Copy the 16–64 px adaptive PNGs from `small`. Do not upscale any small output
or derive the small set from a previously rasterized PNG.
