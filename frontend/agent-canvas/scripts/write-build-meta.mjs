import { createHash } from 'node:crypto'
import { readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const output = resolve(root, '../../server/static/agent-canvas')
const ignored = new Set(['node_modules', '.pytest_cache'])
const ignoredFiles = new Set([
  'tsconfig.app.tsbuildinfo',
  'tsconfig.node.tsbuildinfo',
  'vite.config.d.ts',
  'vite.config.js',
])
const files = []
function walk(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (ignored.has(entry.name) || ignoredFiles.has(entry.name)) continue
    const full = join(dir, entry.name)
    if (entry.isDirectory()) walk(full)
    else if (!full.startsWith(output)) files.push(full)
  }
}
walk(root)
files.sort((a, b) => {
  const left = relative(root, a).replaceAll('\\', '/')
  const right = relative(root, b).replaceAll('\\', '/')
  return left < right ? -1 : left > right ? 1 : 0
})
const digest = createHash('sha256')
for (const file of files) {
  digest.update(relative(root, file).replaceAll('\\', '/'))
  digest.update('\0')
  digest.update(readFileSync(file))
  digest.update('\0')
}
writeFileSync(join(output, 'build-meta.json'), JSON.stringify({
  schema: 1, source_sha256: digest.digest('hex'), node: process.versions.node, sourcemap: false,
}) + '\n')
