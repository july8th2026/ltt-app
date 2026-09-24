// piece-spawn-he-thong.js - thu SPAWN cac nhi phan nam trong C:\Windows\System32.
// System32 von da cap quyen doc/chay cho "ALL APPLICATION PACKAGES", nen neu spawn
// VAN hong o day thi cai hong KHONG phai do ACL cua thu muc dan dung.
// Muc dich: phan biet "AppContainer khong spawn duoc" voi "spawn duoc nhung con bi chan mang".
'use strict';
const { spawnSync } = require('child_process');

const SYS = process.env.SystemRoot + '\\System32\\';
const IP4 = process.env.IP4 || '';

function thu(nhan, exe, args) {
  const r = spawnSync(exe, args, { encoding: 'utf8', timeout: 20000 });
  const err = r.error ? (r.error.code || r.error.message) : 'none';
  const out = (r.stdout || '').trim().replace(/\s+/g, ' ').slice(0, 60);
  const serr = (r.stderr || '').trim().replace(/\s+/g, ' ').slice(0, 60);
  process.stdout.write(`${nhan} status=${r.status} err=${err} out="${out}" stderr="${serr}"\n`);
}

thu('SPAWN_cmd_echo    ', SYS + 'cmd.exe', ['/c', 'echo XIN_CHAO']);
thu('SPAWN_curl_mang   ', SYS + 'curl.exe', ['-s', '-k', '-o', 'NUL', '-w', '%{http_code}', '--max-time', '8', 'https://example.com/']);
if (IP4) {
  thu('SPAWN_curl_rawip  ', SYS + 'curl.exe', ['-s', '-o', 'NUL', '-w', '%{http_code}', '--max-time', '8', '-H', 'Host: example.com', 'http://' + IP4 + '/']);
}
thu('SPAWN_ping_udp_dns ', SYS + 'nslookup.exe', ['example.com', '1.1.1.1']);
