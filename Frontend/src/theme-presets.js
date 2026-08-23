const palettes = {
  light: {
    canvas: "#F6F8F8",
    surface: "#FFFFFF",
    "surface-muted": "#EDF3F2",
    text: "#182026",
    "text-muted": "#627277",
    border: "#DFE7E7",
    primary: "#276A73",
    "primary-text": "#FFFFFF",
    sidebar: "#12181C",
    "sidebar-text": "#F7FBFB",
    focus: "#2F7D89",
  },
  dark: {
    canvas: "#101417",
    surface: "#182026",
    "surface-muted": "#243138",
    text: "#F7FBFB",
    "text-muted": "#B8C7CA",
    border: "#33434A",
    primary: "#58A6B3",
    "primary-text": "#081012",
    sidebar: "#0A0D0F",
    "sidebar-text": "#F7FBFB",
    focus: "#72C7D2",
  },
  "high-contrast": {
    canvas: "#000000",
    surface: "#000000",
    "surface-muted": "#1A1A1A",
    text: "#FFFFFF",
    "text-muted": "#FFFFFF",
    border: "#FFFFFF",
    primary: "#FFFF00",
    "primary-text": "#000000",
    sidebar: "#000000",
    "sidebar-text": "#FFFFFF",
    focus: "#00FFFF",
  },
};

export const BUILT_IN_THEME_SELECTIONS = Object.freeze(
  Object.fromEntries(
    Object.entries(palettes).map(([appearance, tokens]) => [
      appearance,
      Object.freeze({
        themeId: "ups.built-in",
        version: "1.0.0",
        appearance,
        tokens: Object.freeze(tokens),
      }),
    ]),
  ),
);
