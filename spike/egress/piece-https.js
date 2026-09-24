// "Piece" gia lap: dung THANG require('http'/'https') nhu axios/@slack/web-api
// lam ben trong (khong di qua fetch/undici). Muc tieu lay tu bien moi truong TARGET.
const url = require('url');
const TARGET = process.env.TARGET;
if (!TARGET) {
  console.error(JSON.stringify({ ok: false, mode: 'https-raw', error: 'NO_TARGET' }));
  process.exit(2);
}
const u = new url.URL(TARGET);
const mod = u.protocol === 'https:' ? require('https') : require('http');

const req = mod.get(
  {
    hostname: u.hostname,
    port: u.port || (u.protocol === 'https:' ? 443 : 80),
    path: u.pathname + u.search,
    timeout: 4000,
    rejectUnauthorized: false,
  },
  (res) => {
    let body = '';
    res.on('data', (c) => (body += c));
    res.on('end', () => {
      console.log(JSON.stringify({ ok: true, mode: 'https-raw', target: TARGET, status: res.statusCode, body: body.slice(0, 80) }));
      process.exit(0);
    });
  }
);
req.on('timeout', () => {
  console.log(JSON.stringify({ ok: false, mode: 'https-raw', target: TARGET, error: 'TIMEOUT' }));
  req.destroy();
  process.exit(1);
});
req.on('error', (err) => {
  console.log(JSON.stringify({ ok: false, mode: 'https-raw', target: TARGET, error: err.code || err.message }));
  process.exit(1);
});
