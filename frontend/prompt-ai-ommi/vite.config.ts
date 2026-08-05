import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'

export default defineConfig({
  base: '/static/prompt-ai-ommi/',
  plugins: [react()],
  build: {
    outDir: resolve(import.meta.dirname, '../../server/static/prompt-ai-ommi'),
    emptyOutDir: true,
    sourcemap: false,
    manifest: true,
    rollupOptions: { input: resolve(import.meta.dirname, 'src/main.tsx') },
  },
  test: { environment: 'jsdom', setupFiles: './tests/setup.ts' },
})
