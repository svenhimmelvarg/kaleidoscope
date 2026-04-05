import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
export default defineConfig({
  envDir: '..',
  define: {
    'import.meta.env.VITE_RELEASE_FOLDER': JSON.stringify(process.env.VITE_RELEASE_FOLDER),
    'import.meta.env.VITE_INDEX_NAME': JSON.stringify(process.env.VITE_INDEX_NAME),
    'import.meta.env.VITE_INVOKE_METHOD': JSON.stringify(process.env.VITE_INVOKE_METHOD)
  },
  plugins: [svelte()],
  build: {
    outDir: '../kaleidescope/static',
    emptyOutDir: true,
  },
  server: {
    watch: {
      ignored: [
        '**/data/**',
        '**/public/**'
      ]
    },
    proxy: {
      '/workflow': {
        target: process.env.VITE_KALEIDESCOPE_API_URL,
      },
      '/download': {
        target: process.env.VITE_KALEIDESCOPE_API_URL
      },
      '/publish': {
        target: process.env.VITE_KALEIDESCOPE_API_URL
      },
      '/cancel': {
        target: process.env.VITE_KALEIDESCOPE_API_URL
      },
      '/images': {
        target: process.env.VITE_KALEIDESCOPE_API_URL
      },
      '/api': {
        target: process.env.VITE_CONVEX_URL,
        changeOrigin: true,
        ws: true
      }
    }
  }
})
