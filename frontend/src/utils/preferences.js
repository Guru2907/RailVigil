// Chart colours come from the design tokens through CSS variables.
export const chartTheme = {
  grid: "var(--color-line)",
  tick: { fontSize: 11, fill: "var(--color-muted)", fontFamily: "Schibsted Grotesk Variable, ui-sans-serif, sans-serif" },
  tooltip: {
    contentStyle: {
      background: "var(--color-paper)",
      border: "1px solid var(--color-line)",
      borderRadius: 0,
      color: "var(--color-ink)",
      fontSize: 12,
    },
    cursor: { fill: "var(--color-surface-2)" },
  },
  bar: "var(--color-accent)",
};
