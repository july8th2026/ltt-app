// piece-spawn-he-thong-inherit.js - phep thu QUYET DINH cho huong AppContainer.
//
// Spawn nhi phan trong C:\Windows\System32 (thu muc VON cap quyen cho
// "ALL APPLICATION PACKAGES", nen ACL khong phai bien so) va dung stdio:'inherit'
// (nen ong/pipe cung khong phai bien so - ben trong AppContainer spawnSync bang
// pipe bi TREO, do 24/09). Con ghi thang vao dau ra da ke thua cua cha.
//
// Doc ket qua:
//   - Hien "XIN_CHAO"  => AppContainer CO spawn duoc tien trinh con.
//   - Sau do curl in ma 200 => con DA THOAT vong chan mang  (AppContainer HONG vai ranh gioi)
//   - Sau do curl in 000 / loi => con VAN bi chan            (AppContainer DUNG vai ranh gioi)
//   - Khong hien "XIN_CHAO" ma bao loi => AppContainer khong spawn duoc gi ca.
'use strict';
const { spawnSync } = require('child_process');

const SYS = process.env.SystemRoot + '\\System32\\';
const IP4 = process.env.IP4 || '';

function thu(nhan, exe, args) {
  process.stdout.write('--- ' + nhan + ' ---\n');
  const r = spawnSync(exe, args, { stdio: 'inherit', timeout: 20000 });
  const err = r.error ? (r.error.code || r.error.message) : 'none';
  process.stdout.write('\n[' + nhan + '] status=' + r.status + ' err=' + err + '\n');
}

thu('SPAWN_cmd_echo', SYS + 'cmd.exe', ['/c', 'echo XIN_CHAO']);
thu('SPAWN_curl_tcp_host', SYS + 'curl.exe', ['-s', '-k', '-o', 'NUL', '-w', '%{http_code}', '--max-time', '8', 'https://example.com/']);
if (IP4) {
  thu('SPAWN_curl_tcp_rawip', SYS + 'curl.exe', ['-s', '-o', 'NUL', '-w', '%{http_code}', '--max-time', '8', '-H', 'Host: example.com', 'http://' + IP4 + '/']);
}
thu('SPAWN_nslookup_udp53', SYS + 'nslookup.exe', ['example.com', '1.1.1.1']);
