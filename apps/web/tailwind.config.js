/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        flame: {
          50: '#fff7ed',
          100: '#ffedd5',
          200: '#fed7aa',
          300: '#fdba74',
          400: '#fb923c',
          500: '#f97316',
          600: '#ea580c',
          700: '#c2410c',
          800: '#9a3412',
          900: '#7c2d12',
        },
      },
      animation: {
        'flame-flicker': 'flicker 0.5s ease-in-out infinite alternate',
      },
      keyframes: {
        flicker: {
          '0%': { opacity: '1', transform: 'scale(1)' },
          '100%': { opacity: '0.8', transform: 'scale(1.02)' },
        },
      },
    },
  },
  plugins: [],
}
