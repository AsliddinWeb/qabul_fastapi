import type { Config } from 'tailwindcss'

export default <Partial<Config>>{
  darkMode: 'class',
  content: [
    './components/**/*.{vue,js,ts}',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './app.vue',
  ],
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
    },
  },
}
