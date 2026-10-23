import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Port 8000 is taken by the Canvas platform in this environment, so the dev API
// listens on 8010. Override with API_PROXY_TARGET if yours differs.
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8010'
// 5173 is the Vite default, but the Canvas platform's service worker claims
// /api/auth/me there, which drops the session on reload. 5174 is a clean origin.
const devPort = Number(process.env.VITE_DEV_PORT ?? 5174)

export default defineConfig({
  plugins: [react()],
  server: {
    port: devPort,
    proxy: {
      // Keeps the browser talking to one origin, so the session cookie is
      // first-party and no CORS preflight is needed in development.
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
