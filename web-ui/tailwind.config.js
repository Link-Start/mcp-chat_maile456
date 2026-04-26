/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#09090b',
          panel: '#111113',
          card: '#18181b',
          border: '#27272a',
          hover: '#2a2a2e',
          text: '#fafafa',
          muted: '#71717a',
          accent: '#6366f1',
        }
      }
    },
  },
  plugins: [],
}
