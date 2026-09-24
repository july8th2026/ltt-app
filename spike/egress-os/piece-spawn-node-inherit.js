// piece-spawn-node-inherit.js - nhu piece-spawn-node.js nhung KHONG dung ong (pipe):
// con ghi THANG vao dau ra da ke thua cua cha (`stdio: 'inherit'`).
//
// Vi sao can ban nay: ben trong AppContainer, `spawnSync` co bat dau ra bang pipe
// TREO (do 24/09, ca khi co lan khong co capability mang) - tuc phep thu bang pipe
// khong phan biet duoc "con bi chan mang" voi "spawn hong". Ban 'inherit' bo hoan
// toan bien do, nen dong REACHED/BLOCKED trong tep ket qua la do CHINH TIEN TRINH CON in ra.
'use strict';
const { spawnSync } = require('child_process');
const path = require('path');

process.stdout.write('PARENT_DA_CHAY\n');
const r = spawnSync(
  process.execPath,
  ['--preserve-symlinks-main', path.join(__dirname, 'probe.js')],
  { stdio: 'inherit', timeout: 25000, env: process.env }
);
process.stdout.write('PARENT_SPAWN_XONG status=' + r.status + ' err=' + (r.error ? (r.error.code || r.error.message) : 'none') + '\n');
