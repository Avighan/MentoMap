import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// api/*.js clients call apiClient with relative paths like '/api/games' and
// no VITE_API_* base URL is read anywhere in src/ (see docs/RUNNING_LOCALLY.md
// and src/api/client.js) — so in dev, relative /api/* requests need to be
// proxied to the Flask backend on :5001 (matching the port documented in
// docs/RUNNING_LOCALLY.md). In production the app is expected to be served
// from the same origin as the API, so no rewrite is needed.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
    },
  },
});
