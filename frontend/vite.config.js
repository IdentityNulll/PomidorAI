import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
    plugins: [react()],
    build: {
        // FastAPI serves this directory in production.
        outDir: '../backend/static',
        emptyOutDir: true,
    },
    server: {
        port: 5173,
        proxy: {
            '/api': 'http://127.0.0.1:8000',
        },
    },
});
