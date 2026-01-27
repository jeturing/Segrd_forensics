import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { copyFileSync, mkdirSync, readdirSync, statSync } from 'fs'

// Plugin to copy locales folder to dist
const copyLocalesPlugin = () => ({
  name: 'copy-locales',
  writeBundle() {
    const srcLocales = path.resolve(__dirname, 'src/locales')
    const destLocales = path.resolve(__dirname, 'dist/locales')
    
    function copyDir(src, dest) {
      mkdirSync(dest, { recursive: true })
      const entries = readdirSync(src, { withFileTypes: true })
      
      for (const entry of entries) {
        const srcPath = path.join(src, entry.name)
        const destPath = path.join(dest, entry.name)
        
        if (entry.isDirectory()) {
          copyDir(srcPath, destPath)
        } else {
          copyFileSync(srcPath, destPath)
        }
      }
    }
    
    copyDir(srcLocales, destLocales)
    console.log('✓ Copied locales to dist/')
  }
})

export default defineConfig({
  plugins: [react(), copyLocalesPlugin()],
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
