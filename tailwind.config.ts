import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        ivory: {
          50: "#FCFAF6",
          100: "#F8F4EC",
          200: "#F0E8D9",
          300: "#E6D7BE",
        },
        plum: {
          950: "#1C0A1C",
          900: "#2B102B",
          850: "#361536",
          800: "#441D44",
          700: "#5D295D",
          600: "#7A397A",
          200: "#D8BFD8",
          100: "#EEDDF0",
          50: "#F9F3FA",
        },
        marigold: {
          500: "#F59E0B",
          600: "#D97706",
          700: "#B45309",
          400: "#FBBF24",
          300: "#FCD34D",
          100: "#FEF3C7",
        },
      },
    },
  },
  plugins: [],
};
export default config;
