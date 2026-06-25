/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        paper: {
          DEFAULT: "#fdfcfa",
          50: "#ffffff",
          100: "#faf8f4",
          200: "#f3efe7",
          300: "#e8e1d4",
        },
        umber: {
          950: "#2a1d14",
          900: "#3d2b1f",
          800: "#4d3829",
          700: "#5e4534",
          600: "#7a5c46",
          500: "#8b5a3c",
          400: "#a87a52",
          300: "#c9a876",
          200: "#ddc9a3",
          100: "#ede2cd",
        },
        clay: {
          DEFAULT: "#b5673f",
          dim: "#8b5034",
          bright: "#d4895c",
        },
        sage: {
          DEFAULT: "#6b7c5e",
          dim: "#566249",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(139,90,60,0.18), 0 8px 24px -8px rgba(61,43,31,0.18)",
        "glow-clay": "0 0 0 1px rgba(181,103,63,0.22), 0 8px 24px -8px rgba(181,103,63,0.25)",
        card: "0 1px 2px rgba(61,43,31,0.04), 0 4px 12px -4px rgba(61,43,31,0.06)",
      },
      keyframes: {
        pulse_travel: {
          "0%": { strokeDashoffset: "24" },
          "100%": { strokeDashoffset: "0" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "pulse-travel": "pulse_travel 0.8s linear infinite",
        "fade-up": "fade-up 0.4s ease-out",
      },
    },
  },
  plugins: [],
}

