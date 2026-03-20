import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: "#0B0E11",
          secondary: "#1E2026",
          tertiary: "#2B2F36",
        },
        accent: {
          yellow: "#F0B90B",
          green: "#0ECB81",
          red: "#F6465D",
        },
        cbx: {
          text: "#EAECEF",
          muted: "#848E9C",
          border: "#2B2F36",
        },
      },
    },
  },
  plugins: [],
};
export default config;
