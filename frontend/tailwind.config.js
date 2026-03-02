/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#4A90E2',
          light: '#5BA0F2',
          dark: '#3A80D2',
        },
        secondary: {
          DEFAULT: '#F5A623',
          light: '#FFB633',
        },
        success: '#7ED321',
        warning: '#F5A623',
        error: '#E74C3C',
        info: '#4A90E2',
        background: '#F7F9FC',
        surface: '#FFFFFF',
        border: '#E8ECF0',
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'PingFang SC',
          'Hiragino Sans GB',
          'Microsoft YaHei',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
}
