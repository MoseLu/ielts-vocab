import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  root: '.',
  publicDir: 'assets',
  server: {
    host: '0.0.0.0', // 允许所有端口访问
    port: 3002,
    open: true,
    allowedHosts: ['axiomaticworld.com', '.axiomaticworld.com'], // 允许该域名访问
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: true
  },
  resolve: {
    alias: {
      '@': '/src',
      '@assets': '/assets'
    }
  }
})