import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    // Locally, FastAPI serves the bundle itself, so build straight into the
    // directory it serves. On Netlify there is no FastAPI - only the static
    // site - so build to the conventional dist/ that netlify.toml publishes.
    outDir: process.env.NETLIFY ? 'dist' : '../backend/static',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
});
