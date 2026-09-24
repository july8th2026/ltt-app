// piece-spawn-curl.js - "piece doc hai" bac hai: spawn mot NHI PHAN KHAC hoan toan
// (curl.exe cua Windows). Dung lam vat thay the cho "native addon mo socket bang
// syscall truc tiep": neu curl.exe van ra duoc thi co che dang do KHONG phai ranh
// gioi o muc he dieu hanh, no chi la luat gan vao rieng node.exe.
'use strict';
const { spawnSync } = require('child_process');

const MODE = process.env.MODE || 'tcp_host';
const IP4 = process.env.IP4 || '';
const IP6 = process.env.IP6 || '';
const CURL = process.env.SystemRoot + '\\System32\\curl.exe';

let args = null;
if (MODE === 'tcp_host') {
  args = ['-s', '-k', '-o', 'NUL', '-w', '%{http_code}', '--max-time', '8', 'https://example.com/'];
} else if (MODE === 'tcp_rawip' && IP4) {
  args = ['-s', '-o', 'NUL', '-w', '%{http_code}', '--max-time', '8', '-H', 'Host: example.com', 'http://' + IP4 + '/'];
} else if (MODE === 'tcp_ipv6' && IP6) {
  args = ['-s', '-6', '-o', 'NUL', '-w', '%{http_code}', '--max-time', '8', '-H', 'Host: example.com', 'http://[' + IP6 + ']/'];
}

if (!args) {
  process.stdout.write('CHILD_SKIP curl_khong_ho_tro_mode ' + MODE + '\n');
} else {
  const r = spawnSync(CURL, args, { encoding: 'utf8', timeout: 25000 });
  const code = (r.stdout || '').trim();
  if (r.status === 0 && code && code !== '000') {
    process.stdout.write('CHILD_REACHED curl_' + MODE + ' status=' + code + '\n');
  } else {
    process.stdout.write('CHILD_BLOCKED curl_' + MODE + ' exit=' + r.status + ' code=' + (code || 'none') + '\n');
  }
}
