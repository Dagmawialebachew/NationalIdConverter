/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./**/templates/**/*.html",
    "./**/*.py",
  ],
  safelist: [
    // Add dynamically generated classes here if needed
  ],
  theme: {
    extend: {
      colors: {
        gold: { 
          DEFAULT: '#C9A84C', 
          light: '#E0C278', 
          dark: '#9C7C2E', 
          faint: '#C9A84C1A' 
        },
        obsidian: { 
          DEFAULT: '#0A0A0B', 
          2: '#111114', 
          3: '#18181C', 
          4: '#222228', 
          5: '#2C2C35' 
        },
        ivory: { 
          DEFAULT: '#F5F0E8', 
          muted: '#C8C0B0', 
          dim: '#7A7570' 
        },
      },
      fontFamily: {
        display: ['"Cormorant Garamond"', 'Georgia', 'serif'],
        body: ['"DM Sans"', 'sans-serif'],
      },
      backgroundImage: {
        grain: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\' opacity=\'0.04\'/%3E%3C/svg%3E")',
      },
      animation: {
        'fade-up': 'fadeUp 0.6s ease forwards',
        'fade-in': 'fadeIn 0.4s ease forwards',
        'glow-pulse': 'glowPulse 3s ease-in-out infinite',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(18px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        glowPulse: {
          '0%, 100%': { boxShadow: '0 0 20px #C9A84C22' },
          '50%': { boxShadow: '0 0 48px #C9A84C44' },
        },
      },
    },
  },
  plugins: [],
}