import { resolve } from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const DEV_SERVER_PORT = 3020
const PREVIEW_PORT = 3002
const SPEECH_PROXY_PATH = '/speech-socket.io'
const API_PROXY_TARGET = process.env.VITE_API_PROXY_TARGET?.trim() || 'http://127.0.0.1:8000'
const SPEECH_PROXY_TARGET =
  process.env.VITE_SPEECH_PROXY_TARGET?.trim() || 'http://localhost:5001'
const rewriteSpeechSocketPath = (path: string) => path.replace(SPEECH_PROXY_PATH, '/socket.io')

function buildProxyConfig() {
  return {
    '/api': {
      target: API_PROXY_TARGET,
      changeOrigin: true,
      secure: false,
      timeout: 180000,
    },
    '/socket.io': {
      target: SPEECH_PROXY_TARGET,
      changeOrigin: true,
      secure: false,
      ws: true,
    },
    [SPEECH_PROXY_PATH]: {
      target: SPEECH_PROXY_TARGET,
      changeOrigin: true,
      secure: false,
      ws: true,
      rewrite: rewriteSpeechSocketPath,
    },
  }
}

export default defineConfig({
  plugins: [react()],
  root: __dirname,
  publicDir: 'assets',
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler',
      },
    },
  },
  server: {
    host: true, // Bind localhost without forcing IPv4-only fallback delays
    port: DEV_SERVER_PORT,
    strictPort: true, // Fail instead of switching ports when 3020 is occupied
    open: false,
    allowedHosts: true, // Accept requests from any host in local proxy setups
    hmr: {
      overlay: true,
      // Prevent full-page reload on HMR WebSocket reconnection
      timeout: 30000,
    },
    proxy: buildProxyConfig(),
  },
  build: {
    outDir: '../dist',
    assetsDir: 'assets',
    emptyOutDir: true,
    sourcemap: false,
    chunkSizeWarningLimit: 1000,
  },
  preview: {
    host: true,
    port: PREVIEW_PORT,
    strictPort: true,
    allowedHosts: true,
    // Disable HMR overlay in preview mode
    hmr: false,
    // Preview mode needs the same proxy rules, or /api requests hit Vite directly and 404.
    proxy: buildProxyConfig(),
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@assets': resolve(__dirname, 'assets'),
    }
  }
})
