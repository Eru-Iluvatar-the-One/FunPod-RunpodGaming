import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import electron from 'vite-plugin-electron/simple'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    react(),
    electron({
      main: { entry: 'electron/main.js' },
      preload: { input: 'electron/preload.js' },
    }),
  ],
  resolve: { alias: { '@': resolve(__dirname, './src') } },
  server: { port: 5173 },
})
