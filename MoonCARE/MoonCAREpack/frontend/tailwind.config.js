/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // MoonCARE Design System
        primary: {
          DEFAULT: '#EC4899',  // pink-500
          light: '#F472B6',   // pink-400
          dark: '#DB2777',    // pink-600
          50: '#FDF2F8',
          100: '#FCE7F3',
          200: '#FBCFE8',
          300: '#F9A8D4',
          400: '#F472B6',
          500: '#EC4899',
          600: '#DB2777',
          700: '#BE185D',
        },
        secondary: {
          DEFAULT: '#8B5CF6',  // purple-500
          light: '#A78BFA',
          dark: '#7C3AED',
        },
        accent: {
          DEFAULT: '#F97316',  // orange-500
          light: '#FB923C',
          dark: '#EA580C',
        },
        surface: {
          bg: '#F9FAFB',
          card: '#FFFFFF',
          muted: '#64748B',
        },
        emotion: {
          depression: '#A855F7',  // purple
          anxiety: '#F97316',     // orange
          anger: '#EF4444',       // red
          calm: '#22C55E',        // green
        }
      },
      fontFamily: {
        sans: ['PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'card': '12px',  // rounded-xl
        'button': '9999px',  // rounded-full
      },
      spacing: {
        'card': '16px',
        'card-sm': '12px',
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgb(0 0 0 / 0.05)',
        'card-hover': '0 4px 6px -1px rgb(0 0 0 / 0.1)',
      }
    },
  },
  plugins: [],
}
