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
          blue: '#0A4287',     // Azul Institucional AULA USM (exacto de la barra superior)
          dark: '#072F60',     // Azul más profundo para estados activos y bordes
          light: '#EAF2F9',    // Azul suave para fondos y selecciones
          gold: '#F2A900',     // Amarillo USM
          red: '#C9281D',      // Rojo USM (como el indicador de notificaciones de AULA)
        }
      }
    },
  },
  plugins: [],
}
