// May chu bat egress cuc bo, dai dien "internet" trong ban thu.
// Nghe ca IPv4 va IPv6 tren hai cong rieng de tranh nhap nhang dual-stack cua Windows.
const http = require('http');

const PORT_V4 = 18199;
const PORT_V6 = 18299;

function makeServer(label) {
  return http.createServer((req, res) => {
    console.log(`[catcher:${label}] HIT ${req.method} ${req.url} from ${req.socket.remoteAddress}`);
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end(`caught:${label}\n`);
  });
}

const s4 = makeServer('v4');
s4.listen(PORT_V4, '127.0.0.1', () => {
  console.log(`[catcher] IPv4 listening on 127.0.0.1:${PORT_V4}`);
});

const s6 = makeServer('v6');
s6.listen(PORT_V6, '::1', () => {
  console.log(`[catcher] IPv6 listening on [::1]:${PORT_V6}`);
});
