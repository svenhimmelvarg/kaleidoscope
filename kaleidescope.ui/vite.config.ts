import { defineConfig, loadEnv } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '')
  const apiUrl = process.env.KALEIDESCOPE_API_URL || env.VITE_KALEIDESCOPE_API_URL || env.KALEIDESCOPE_API_URL || 'http://localhost:8000'
  const convexUrl = process.env.CONVEX_URL || env.CONVEX_URL || 'http://127.0.0.1:3210'

  return {
    define: {
      'import.meta.env.VITE_RELEASE_FOLDER': JSON.stringify(process.env.RELEASE_FOLDER || env.RELEASE_FOLDER || 'release'),
      'import.meta.env.VITE_INDEX_NAME': JSON.stringify(process.env.INDEX_NAME || env.INDEX_NAME || 'comfy_outputs_v110'),
      'import.meta.env.VITE_INVOKE_METHOD': JSON.stringify(process.env.INVOKE_METHOD || env.INVOKE_METHOD || 'invoke')
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
          target: apiUrl,
        },
        '/download': {
          target: apiUrl
        },
        '/publish': {
          target: apiUrl
        },
        '/cancel': {
          target: apiUrl
        },
        '/images': {
          target: apiUrl
        },
        '/api': {
          target: convexUrl,
          changeOrigin: true,
          ws: true
        }
      }
    }
  }
})
