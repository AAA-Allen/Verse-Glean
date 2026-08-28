import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // 开发期代理到 FastAPI，避免跨域；生产由 Nginx 承担
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
