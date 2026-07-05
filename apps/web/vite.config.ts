import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev proxy: browser talks to Vite on :5173, which forwards /api to the
// local NEXUS backend on :8400. Keeps everything loopback-only.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:8400' },
  },
})
