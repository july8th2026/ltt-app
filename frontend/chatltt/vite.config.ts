import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'

export default defineConfig({
  base: '/static/chatltt/',
  plugins: [react()],
  build: {
    outDir: resolve(import.meta.dirname, '../../server/static/chatltt'),
    emptyOutDir: true,
    sourcemap: false,
    manifest: true,
    rollupOptions: { input: resolve(import.meta.dirname, 'src/main.tsx') },
  },
  test: {
    environment: 'jsdom',
    // 20s, cung ly do da ghi o `frontend/agent-canvas/vite.config.ts`: mac dinh
    // 5s chi hon test cham nhat ~1,7 giay, nen khi may ban (hai phien Claude,
    // bon cum pytest, mot luot deploy) thi buoc gate do vi MAY, khong vi MA.
    // Mot gate chap chon thi khong con la bang chung.
    testTimeout: 20_000,
    hookTimeout: 20_000,
    setupFiles: './tests/setup.ts',
  },
})
