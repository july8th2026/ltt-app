import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'

export default defineConfig({
  base: '/static/autosub-studio/',
  plugins: [react()],
  build: {
    outDir: resolve(import.meta.dirname, '../../server/static/autosub-studio'),
    emptyOutDir: true,
    sourcemap: false,
    manifest: true,
    rollupOptions: { input: resolve(import.meta.dirname, 'src/main.tsx') },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './tests/setup.ts',
    // Xem chu thich day du o `frontend/agent-canvas/vite.config.ts`: mac dinh
    // 5000ms qua sat khi may ban, va mot buoc gate chap chon lam ca cai gate
    // mat gia tri lam bang chung.
    testTimeout: 20_000,
    hookTimeout: 20_000,
  },
})
