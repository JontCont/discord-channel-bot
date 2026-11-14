import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// `vite --mode mock` serves the app against an in-memory mock API (no login, no backend).
export default defineConfig(({ mode }) => ({
  define: {
    'import.meta.env.VITE_MOCK': JSON.stringify(mode === 'mock' ? 'true' : 'false'),
  },
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
}))