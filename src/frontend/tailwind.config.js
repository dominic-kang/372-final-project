/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        duke: {
          blue:  '#003087',
          navy:  '#012169',
          light: '#4a90d9',
        },
      },
    },
  },
  plugins: [],
}
