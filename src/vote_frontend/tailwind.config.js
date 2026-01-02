/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'splat-orange': '#f54910',
        'splat-purple': '#603bff',
        'splat-green': '#00ff00',
        'splat-pink': '#ff00ff',
      },
    },
  },
  plugins: [],
}
