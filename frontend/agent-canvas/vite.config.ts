import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'

export default defineConfig({
  base: '/static/agent-canvas/',
  plugins: [react()],
  build: {
    outDir: resolve(import.meta.dirname, '../../server/static/agent-canvas'),
    emptyOutDir: true,
    sourcemap: false,
    manifest: true,
    rollupOptions: { input: resolve(import.meta.dirname, 'src/main.tsx') },
  },
  test: {
    environment: 'jsdom',
    // Mac dinh cua vitest la 5000ms. Do ngay 25/08 tren may RANH: test cham
    // nhat cua agent-canvas mat 3288ms — bien chi 1,7 giay.
    //
    // Hau qua: khi may ban (hai phien Claude chay song song, bon cum pytest,
    // mot luot deploy), test do vuot 5s va DO. Chay lai thi xanh. Mot buoc
    // gate chap chon lam ca cai gate mat gia tri lam bang chung — nguoi doc
    // khong con phan biet duoc "do that" voi "do vi may ban".
    //
    // 20s KHONG giau mot test treo: treo van do, chi la do muon hon. No chi
    // bo cai bien qua mong giua "cham" va "hong".
    testTimeout: 20_000,
    hookTimeout: 20_000,
    setupFiles: './tests/setup.ts',
  },
})
