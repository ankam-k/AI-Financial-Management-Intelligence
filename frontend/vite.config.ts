import react from '@vitejs/plugin-react';
// `vitest/config` re-exports Vite's defineConfig with the `test` block typed,
// so one file configures both the dev server and the test runner.
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // The dev server proxies /api to the backend, so the browser only ever
    // talks to one origin. That is why the backend needs no CORS
    // configuration for local development — a same-origin request is not
    // subject to it. A deployed build sits behind the same reverse proxy
    // (10_Deployment.md), so the arrangement holds in production too.
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
