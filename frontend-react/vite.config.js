import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.js',
  },
  server: {
    port: 3001,  // App runs on 3001, public website on 3000
    strictPort: true,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:9000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api')
      },
      '/ws': {
        target: 'ws://localhost:9000',
        ws: true,
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['react', 'react-dom', 'react-router-dom'],
          'redux': ['@reduxjs/toolkit', 'react-redux'],
          'ui': ['@mui/material', '@mui/icons-material']
        }
      }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
})
