import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://localhost:8080'
    }
  },
  build: {
    outDir: '../../static',
    emptyOutDir: true
  }
})
