import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  root: '.',
  publicDir: 'assets',
  server: {
    host: '0.0.0.0', // 允许所有端口访问
    port: 3002,
    strictPort: true, // 端口被占用时报错而非切换端口
    open: false,
    allowedHosts: true, // 允许所有域名访问
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
        timeout: 10000,
      },
      '/socket.io': {
        target: 'http://localhost:5000',
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
    port: 3002,
    strictPort: true,
    allowedHosts: true,
    // Disable HMR overlay in preview mode
    hmr: false,
    // preview 模式同样需要代理，否则 /api 请求打到 vite 自身会 404
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
        timeout: 15000,
      },
      '/socket.io': {
        target: 'http://localhost:5000',
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