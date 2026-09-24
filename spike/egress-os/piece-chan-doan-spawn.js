// piece-chan-doan-spawn.js - loai tru gia thuyet "ENOENT la do THIEU BIEN MOI TRUONG",
// khong phai do AppContainer chan tao tien trinh.
// In ra bien moi truong that su nhin thay duoc, va spawn bang duong dan VIET CUNG.
'use strict';
const { spawnSync } = require('child_process');
const fs = require('fs');

process.stdout.write('SystemRoot=' + JSON.stringify(process.env.SystemRoot) + '\n');
process.stdout.write('PATH_co=' + (process.env.PATH ? 'co' : 'KHONG') + '\n');
process.stdout.write('so_bien_moi_truong=' + Object.keys(process.env).length + '\n');
process.stdout.write('execPath=' + process.execPath + '\n');

for (const p of ['C:\\Windows\\System32\\cmd.exe', process.execPath]) {
  let doc = 'khong';
  try { fs.accessSync(p, fs.constants.R_OK); doc = 'co'; } catch (e) { doc = 'khong (' + e.code + ')'; }
  let stat = 'khong';
  try { stat = 'co (' + fs.statSync(p).size + ' byte)'; } catch (e) { stat = 'khong (' + e.code + ')'; }
  process.stdout.write('TEP ' + p + ' -> doc duoc=' + doc + ' stat=' + stat + '\n');
  const r = spawnSync(p, ['/c', 'echo XIN_CHAO'], { stdio: 'inherit', timeout: 15000 });
  process.stdout.write('  spawn -> status=' + r.status + ' err=' + (r.error ? (r.error.code || r.error.message) : 'none') + '\n');
}
