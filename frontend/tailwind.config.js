/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#eef4ff',
          100: '#dae6ff',
          200: '#b8ccff',
          300: '#8fa9ff',
          400: '#647ffb',
          500: '#3f56ef',
          600: '#2d3dd1',
          700: '#2530a4',
          800: '#1f2880',
          900: '#1a2167',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'card':       '0 1px 2px 0 rgb(0 0 0 / 0.04), 0 0 0 1px rgb(0 0 0 / 0.04)',
        'card-dark':  '0 1px 2px 0 rgb(0 0 0 / 0.4), 0 0 0 1px rgb(255 255 255 / 0.06)',
        'dropdown':   '0 10px 30px -10px rgb(0 0 0 / 0.18), 0 4px 12px -4px rgb(0 0 0 / 0.08)',
      },
    },
  },
  plugins: [],
}
