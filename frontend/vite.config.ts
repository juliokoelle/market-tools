import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

function classicScript() {
  return {
    name: 'classic-script',
    transformIndexHtml(html: string) {
      return html
        .replace(/ type="module"/g, ' defer')
        .replace(/ crossorigin/g, '')
    },
  }
}

export default defineConfig({
  plugins: [react(), classicScript()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  build: {
    rollupOptions: {
      output: {
        format: 'iife',
        name: 'App',
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
})
