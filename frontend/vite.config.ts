import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Documented Requirement: React + Vite (§11)
// Implementation Assumption: path alias '@' → src/, proxy to FastAPI on :8000
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/query': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  build: {
    // Performance budget: < 350KB gzipped initial bundle (§13)
    // Charts are lazy-split — Plotly only loads when chart components render
    chunkSizeWarningLimit: 2000,  // Plotly.js is intentionally large; suppress warning
    rollupOptions: {
      output: {
        // Vite 8 / rolldown requires manualChunks as a function
        manualChunks: (id: string) => {
          if (id.includes('recharts'))          return 'charts-recharts'
          if (id.includes('plotly') || id.includes('react-plotly')) return 'charts-plotly'
          if (id.includes('framer-motion'))     return 'motion'
          if (id.includes('react-json-view'))   return 'json-view'
        },
      },
    },
  },
})
