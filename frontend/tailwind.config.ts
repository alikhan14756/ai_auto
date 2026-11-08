import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        canvas: {
          base: "#090A0D",
          card: "#111318",
          subtle: "#181B22",
          border: "#222631",
        },
        ember: {
          DEFAULT: "#FF7A00",
          hover: "#FF8F26",
          active: "#E05D00",
          muted: "rgba(255, 122, 0, 0.10)",
          glow: "rgba(255, 122, 0, 0.25)",
        },
        status: {
          success: "#10B981",
          warning: "#F59E0B",
          error: "#EF4444",
          info: "#3B82F6",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
