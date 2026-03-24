import { defineConfig, loadEnv } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '')
  const apiUrl = env.VITE_KALEIDESCOPE_API_URL //  || 'http://localhost:8000'
  const convexUrl = env.CONVEX_URL  //   || 'http://127.0.0.1:3210'

  return {
    define: {
      'import.meta.env.VITE_RELEASE_FOLDER': JSON.stringify(env.RELEASE_FOLDER || 'release'),
      'import.meta.env.VITE_INDEX_NAME': JSON.stringify(env.INDEX_NAME || 'comfy_outputs_v110')
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
