const defaultTheme = require('tailwindcss/defaultTheme');

module.exports = {
  content: [
    './src/app/**/*.{js,ts,jsx,tsx}',
    './src/app/pages/**/*.{js,ts,jsx,tsx}',
    './src/app/components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        capiPrimary: '#2916b4',
        capiAccent: '#00eaff',
        capiBgDark: 'hsl(212,53%,13%)'
      },
      boxShadow: {
        glow: '0 0 10px 2px rgba(0,188,255,0.4)'
      },
      animation: {
        'pulse-capi': 'pulse-capi 2.5s infinite'
      },
      keyframes: {
        'pulse-capi': {
          '0%': { boxShadow: '0 0 0 0 #00eaff55', opacity: '1' },
          '70%': { boxShadow: '0 0 40px 60px #00eaff11', opacity: '.7' },
          '100%': { boxShadow: '0 0 0 0 #00eaff00', opacity: '1' }
        }
      }
    },
    fontFamily: {
      sans: ['Inter', ...defaultTheme.fontFamily.sans]
    }
  },
  plugins: [],
};
