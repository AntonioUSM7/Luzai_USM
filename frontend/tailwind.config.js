/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        display: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        usm: {
          blue: '#0052CC',      // Azul institucional más vivo
          electric: '#1D6FFF',  // Azul eléctrico para degradados y foco
          cyan: '#00A8E8',      // Cian luminoso de apoyo
          dark: '#06285A',      // Azul profundo de contraste
          light: '#EFF6FF',     // Tinte claro
          gold: '#FFB000',      // Amarillo USM vibrante
          red: '#E11D2E',       // Rojo USM vivo
        }
      }
    },
  },
  plugins: [],
}
