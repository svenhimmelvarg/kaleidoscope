import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
export default defineConfig(() => {

  const requireEnv = (name: string) => {
    if (process.env[name]) {
      return process.env[name]
    }
    throw new Error(`Missing required environment variable: ${name}`)
  }

  const apiUrl = requireEnv('VITE_KALEIDESCOPE_API_URL')
  const convexUrl = requireEnv('VITE_CONVEX_URL')

  return {
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
