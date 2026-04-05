import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const DEV_SERVER_PORT = 3020
const PREVIEW_PORT = 3002

export default defineConfig({
  plugins: [react()],
  root: '.',
  publicDir: 'assets',
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler',
      },
    },
  },
  server: {
    host: '0.0.0.0', // Allow access from any local interface
    port: DEV_SERVER_PORT,
    strictPort: true, // Fail instead of switching ports when 3020 is occupied
    open: false,
    allowedHosts: true, // Accept requests from any host in local proxy setups
    hmr: {
      overlay: true,
      // Prevent full-page reload on HMR WebSocket reconnection
      timeout: 30000,
    },
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
        timeout: 180000,
      },
      '/socket.io': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
        ws: true,
      },
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    chunkSizeWarningLimit: 1000,
  },
  preview: {
    host: '0.0.0.0',
    port: PREVIEW_PORT,
    strictPort: true,
    allowedHosts: true,
    // Disable HMR overlay in preview mode
    hmr: false,
    // Preview mode needs the same proxy rules, or /api requests hit Vite directly and 404.
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
        timeout: 180000,
      },
      '/socket.io': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
        ws: true,
      },
    },
  },
  resolve: {
    alias: {
      '@': '/src',
      '@assets': '/assets'
    }
  }
})
