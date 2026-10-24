import { useEffect, useState } from "react";

// Per-viewer display preferences (theme and text size), kept in localStorage.
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

export const TEXT_SIZES = [
  ["sm", "A−", "14px"],
  ["md", "A", "16px"],
  ["lg", "A+", "18px"],
];

export function applyStoredPreferences() {
  document.documentElement.dataset.theme = read("rv-theme", "tactical");
  const size = TEXT_SIZES.find(([k]) => k === read("rv-text", "md"));
  document.documentElement.style.fontSize = size ? size[2] : "16px";
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

export const setTextSize = (key) => {
  const size = TEXT_SIZES.find(([k]) => k === key);
  document.documentElement.style.fontSize = size ? size[2] : "16px";
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
