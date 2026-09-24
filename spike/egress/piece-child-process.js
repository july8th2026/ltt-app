// Piece "doc hai": khong tu goi mang, ma DE mot tien trinh con goi ho.
// Tien trinh con KHONG duoc nap preload (`-r` khong di theo spawn),
// nen no la duong vong qua moi ban va trong-tien-trinh.
const { spawnSync } = require('child_process');
const ma = "require('https').get('https://example.com/', r => {" +
           "console.log('CHILD_REACHED ' + r.statusCode); process.exit(0);})" +
           ".on('error', e => {console.log('CHILD_BLOCKED ' + e.message); process.exit(0);});";
const r = spawnSync(process.execPath, ['-e', ma], { encoding: 'utf8', timeout: 20000 });
console.log((r.stdout || '').trim() || ('NO_OUTPUT ' + (r.stderr || '').trim().slice(0, 200)));
