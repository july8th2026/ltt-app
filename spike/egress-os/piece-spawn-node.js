// piece-spawn-node.js - "piece doc hai": khong tu goi mang, de TIEN TRINH CON goi ho.
// Day la dung phep thu da lam thung moi ban va trong-tien-trinh o spike P6
// (`spike/egress/piece-child-process.js`), mo rong them cho tung MODE.
'use strict';
const { spawnSync } = require('child_process');
const path = require('path');

const r = spawnSync(process.execPath, [path.join(__dirname, 'probe.js')], {
  encoding: 'utf8',
  timeout: 25000,
  env: process.env,
});
const out = (r.stdout || '').trim().split('\n').filter(Boolean).pop();
if (out) {
  process.stdout.write('CHILD_' + out + '\n');
} else {
  const err = (r.stderr || '').trim().replace(/\s+/g, ' ').slice(0, 160);
  process.stdout.write('CHILD_BLOCKED spawn_failed ' + (r.error ? r.error.code || r.error.message : '') + ' ' + err + '\n');
}
