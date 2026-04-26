import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/status': 'http://127.0.0.1:8080',
      '/submit': 'http://127.0.0.1:8080',
      '/sessions': 'http://127.0.0.1:8080',
      '/poll': 'http://127.0.0.1:8080',
      '/delete': 'http://127.0.0.1:8080',
      '/delete-project': 'http://127.0.0.1:8080',
      '/history': 'http://127.0.0.1:8080',
      '/api': 'http://127.0.0.1:8080',
    }
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      output: {
        manualChunks: {
          'hljs': ['highlight.js'],
          'markdown': ['markdown-it'],
          'vue-vendor': ['vue'],
        }
      }
    }
  }
})
