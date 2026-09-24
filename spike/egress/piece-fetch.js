// "Piece" dung fetch() toan cuc (chay tren undici noi bo cua Node) - de doi chieu voi
// require('http'/'https'): day la duong DUY NHAT undici global dispatcher thuc su chan duoc.
const TARGET = process.env.TARGET;
if (!TARGET) {
  console.error(JSON.stringify({ ok: false, mode: 'fetch', error: 'NO_TARGET' }));
  process.exit(2);
}
const ctrl = new AbortController();
const t = setTimeout(() => ctrl.abort(), 4000);
fetch(TARGET, { signal: ctrl.signal })
  .then(async (res) => {
    clearTimeout(t);
    const body = await res.text();
    console.log(JSON.stringify({ ok: true, mode: 'fetch', target: TARGET, status: res.status, body: body.slice(0, 80) }));
    process.exit(0);
  })
  .catch((err) => {
    clearTimeout(t);
    console.log(JSON.stringify({ ok: false, mode: 'fetch', target: TARGET, error: err.cause?.code || err.code || err.message }));
    process.exit(1);
  });
