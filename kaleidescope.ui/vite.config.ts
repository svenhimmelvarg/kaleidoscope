import { defineConfig, loadEnv } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '')

  const requireEnv = (names: string[]) => {
    for (const name of names) {
      if (process.env[name] || env[name]) {
        return process.env[name] || env[name]
      }
    }
    throw new Error(`Missing required environment variable. Must provide one of: ${names.join(', ')}`)
  }

  const apiUrl = requireEnv(['KALEIDESCOPE_API_URL', 'VITE_KALEIDESCOPE_API_URL'])
  const convexUrl = requireEnv(['CONVEX_URL'])

  return {
    define: {
      'import.meta.env.VITE_RELEASE_FOLDER': JSON.stringify(requireEnv(['RELEASE_FOLDER'])),
      'import.meta.env.VITE_INDEX_NAME': JSON.stringify(requireEnv(['INDEX_NAME'])),
      'import.meta.env.VITE_INVOKE_METHOD': JSON.stringify(requireEnv(['INVOKE_METHOD']))
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
