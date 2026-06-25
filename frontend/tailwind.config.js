/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        background: '#F2F1EF',
        card: '#FFFFFF',
        primary: '#3239A0',
        heading: '#0F172B',
      },
    },
  },
  plugins: [],
}
