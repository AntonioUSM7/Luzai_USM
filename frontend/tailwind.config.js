/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        usm: {
          navy: '#002B49',
          blue: '#004B87',
          gold: '#F2A900',
          red: '#D52B1E',
        }
      }
    },
  },
  plugins: [],
}
