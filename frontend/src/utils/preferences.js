// Chart colours come from the design tokens through CSS variables.
export const chartTheme = {
  grid: "var(--color-line)",
  tick: { fontSize: 11, fill: "var(--color-muted)", fontFamily: "Geist Mono Variable, ui-monospace, monospace" },
  tooltip: {
    contentStyle: {
      background: "var(--color-paper)",
      border: "1px solid var(--color-line)",
      borderRadius: 8,
      color: "var(--color-ink)",
      fontSize: 12,
    },
    cursor: { fill: "var(--color-surface-2)" },
  },
  bar: "var(--color-accent)",
};
