import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Port 8000 is taken by the Canvas platform in this environment, so the dev API
// listens on 8010. Override with API_PROXY_TARGET if yours differs.
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8010'

export default defineConfig({
  plugins: [react()],
  server: {
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
