/**
 * Theme registry — the single source of truth for the configurable palettes.
 *
 * Each id maps to a `[data-theme="..."]` block in app/globals.css. Adding a
 * palette = add an entry here + the matching CSS block; the switcher and every
 * component pick it up automatically (they only read semantic CSS vars).
 */

export type ThemeId = "brand" | "midnight" | "classic" | "basil";

export interface ThemeMeta {
  id: ThemeId;
  label: string;
  description: string;
  scheme: "dark" | "light";
  /** Representative hexes for the switcher swatch only (not used for styling). */
  swatch: { primary: string; accent: string; background: string };
}

export const THEMES: ThemeMeta[] = [
  {
    id: "brand",
    label: "Signature",
    description: "Red, navy & white — the SliceMatic house palette.",
    scheme: "light",
    swatch: { primary: "#e31837", accent: "#0c2340", background: "#ffffff" },
  },
  {
    id: "midnight",
    label: "Midnight",
    description: "Dark, premium — amber glow on near-black.",
    scheme: "dark",
    swatch: { primary: "#f59e0b", accent: "#f97316", background: "#0c0a09" },
  },
  {
    id: "classic",
    label: "Classic",
    description: "Appetizing orange + trust blue on warm cream.",
    scheme: "light",
    swatch: { primary: "#ea580c", accent: "#2563eb", background: "#fff7ed" },
  },
  {
    id: "basil",
    label: "Fresh Basil",
    description: "Artisanal tomato red + basil green on linen.",
    scheme: "light",
    swatch: { primary: "#dc2626", accent: "#16a34a", background: "#fffbeb" },
  },
];

export const DEFAULT_THEME: ThemeId = "midnight";
export const THEME_STORAGE_KEY = "slicematic-theme";

export function isThemeId(value: string | null | undefined): value is ThemeId {
  return !!value && THEMES.some((t) => t.id === value);
}
