import { useEffect, useState } from "react";

// Per-viewer display preference (colour theme), kept in localStorage.
// Storage can be unavailable (private mode), so every access is guarded.

function read(key, fallback) {
  try {
    return localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* ignore */
  }
}

export const THEMES = [
  ["tactical", "Tactical"],
  ["obsidian", "Obsidian"],
];

export function applyStoredPreferences() {
  document.documentElement.dataset.theme = read("rv-theme", "tactical");
}

export function usePreference(key, fallback, apply) {
  const [value, setValue] = useState(() => read(key, fallback));
  useEffect(() => {
    apply(value);
    write(key, value);
  }, [key, value, apply]);
  return [value, setValue];
}

export const setThemeAttr = (theme) => {
  document.documentElement.dataset.theme = theme;
};

// Chart colours follow the active theme through CSS variables.
export const chartTheme = {
  grid: "var(--color-line)",
  tick: { fontSize: 11, fill: "var(--color-muted)", fontFamily: "JetBrains Mono, ui-monospace, monospace" },
  tooltip: {
    contentStyle: {
      background: "var(--color-paper)",
      border: "1px solid var(--color-line)",
      borderRadius: 6,
      color: "var(--color-ink)",
      fontSize: 12,
    },
    cursor: { fill: "var(--color-surface-2)" },
  },
  bar: "var(--color-accent)",
};
