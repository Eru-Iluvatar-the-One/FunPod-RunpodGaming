/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        base: '#1e1e2e', mantle: '#181825', crust: '#11111b',
        surface0: '#313244', surface1: '#45475a', surface2: '#585b70',
        overlay0: '#6c7086', text: '#cdd6f4', subtext0: '#a6adc8',
        blue: '#89b4fa', green: '#a6e3a1', red: '#f38ba8',
        peach: '#fab387', yellow: '#f9e2af', mauve: '#cba6f7',
        teal: '#94e2d5', sapphire: '#74c7ec',
      },
      keyframes: {
        glow: { '0%,100%': { opacity: '0.6' }, '50%': { opacity: '1' } },
        spin1: { to: { transform: 'rotate(360deg)' } },
      },
      animation: {
        glow: 'glow 2s ease-in-out infinite',
        spin1: 'spin1 1s linear infinite',
      },
      fontFamily: {
        ui: ['Segoe UI Variable', 'Inter', 'Segoe UI', 'sans-serif'],
        mono: ['Cascadia Code', 'JetBrains Mono', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
