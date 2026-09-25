/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        "tactical-canvas": "#022C22",
        "tactical-card": "#F0FDF4",
        "tactical-dark": "#18181B",
        "tactical-alert": "#E11D48",
        "tactical-mint": "#34D399",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};