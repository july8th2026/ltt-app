import { createHash } from 'node:crypto'
import { readdir, readFile, writeFile } from 'node:fs/promises'
import { resolve, relative } from 'node:path'

const source = resolve(import.meta.dirname, '..')
const output = resolve(source, '../../server/static/autosub-studio')
const ignoredDirs = new Set(['node_modules', '.pytest_cache'])
const ignoredFiles = new Set(['tsconfig.app.tsbuildinfo', 'tsconfig.node.tsbuildinfo',
  'vite.config.d.ts', 'vite.config.js'])
const inputs = []
async function walk(dir) {
  for (const item of await readdir(dir, { withFileTypes: true })) {
    if (item.isDirectory() && ignoredDirs.has(item.name)) continue
    const full = resolve(dir, item.name)
    if (item.isDirectory()) await walk(full)
    else if (!ignoredFiles.has(item.name)) inputs.push(full)
  }
}
await walk(source)
const hash = createHash('sha256')
for (const full of inputs.sort()) {
  hash.update(relative(source, full).replaceAll('\\', '/')); hash.update('\0')
  hash.update(await readFile(full)); hash.update('\0')
}
await writeFile(resolve(output, 'build-meta.json'), JSON.stringify({
  schema: 1, source_sha256: hash.digest('hex'), node: '24.17.0', sourcemap: false,
}, null, 2) + '\n', 'utf8')
