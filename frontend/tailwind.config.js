/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        space: {
          900: '#0a0f1d',
          800: '#0f172a',
          700: '#1e293b',
          600: '#334155',
        },
        isro: {
          orange: '#ff6600',
          blue: '#0055a5',
          cyan: '#00c2cb',
        }
      }
    },
  },
  plugins: [],
}
