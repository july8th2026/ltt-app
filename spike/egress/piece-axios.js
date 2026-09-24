// "Piece" gia lap dung axios (dai dien cho @slack/web-api va cac SDK dung axios ben trong).
// axios mac dinh dung http.Agent/https.Agent (tuc la module http/https cua Node), KHONG di
// qua undici/fetch tru khi cau hinh adapter fetch tuong minh.
const path = require('path');
const axios = require(path.join(__dirname, 'node_modules', 'axios'));

const TARGET = process.env.TARGET;
if (!TARGET) {
  console.error(JSON.stringify({ ok: false, mode: 'axios', error: 'NO_TARGET' }));
  process.exit(2);
}

axios
  .get(TARGET, { timeout: 4000, httpsAgent: new (require('https').Agent)({ rejectUnauthorized: false }) })
  .then((res) => {
    console.log(JSON.stringify({ ok: true, mode: 'axios', target: TARGET, status: res.status, body: String(res.data).slice(0, 80) }));
    process.exit(0);
  })
  .catch((err) => {
    console.log(JSON.stringify({ ok: false, mode: 'axios', target: TARGET, error: (err.code || err.message || 'ERR') }));
    process.exit(1);
  });
