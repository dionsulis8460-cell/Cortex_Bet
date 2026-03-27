/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#02050a",
        foreground: "#e0e0e0",
        primary: {
          DEFAULT: "#00d2ff",
          dark: "#00a1c2",
        },
        secondary: "#1a1f2e",
        accent: "#ff4b4b",
      },
      backgroundImage: {
        "glass-gradient": "linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.01))",
      },
      boxShadow: {
        "premium": "0 10px 30px -5px rgba(0, 210, 255, 0.2)",
      }
    },
  },
  plugins: [],
};
