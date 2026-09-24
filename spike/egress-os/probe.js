// probe.js - mot phep thu egress DUY NHAT, chon bang bien moi truong MODE.
// In DUNG mot dong: "REACHED <chi tiet>" hoac "BLOCKED <ma loi>".
// Dia chi IP duoc TRUYEN VAO qua env (IP4/IP6) de phep thu khong phu thuoc DNS
// - nhu the mot co che chi chan DNS khong the gia vo la da chan egress.
'use strict';

const MODE = process.env.MODE || 'tcp_host';
const IP4 = process.env.IP4 || '';
const IP6 = process.env.IP6 || '';
const TIMEOUT = 8000;

function done(line) {
  process.stdout.write(line + '\n');
  try { process.stdout.fd && require('fs').fsyncSync(process.stdout.fd); } catch (e) {}
  process.exit(0);
}

function httpGet(opts, label) {
  const mod = opts.protocol === 'https:' ? require('https') : require('http');
  const req = mod.get(opts, (res) => {
    res.resume();
    done('REACHED ' + label + ' status=' + res.statusCode);
  });
  req.setTimeout(TIMEOUT, () => { req.destroy(); done('BLOCKED ' + label + ' TIMEOUT'); });
  req.on('error', (e) => done('BLOCKED ' + label + ' ' + (e.code || e.message)));
}

if (MODE === 'tcp_host') {
  httpGet({ protocol: 'https:', hostname: 'example.com', port: 443, path: '/', timeout: TIMEOUT, rejectUnauthorized: false }, 'tcp_host');
} else if (MODE === 'tcp_rawip') {
  if (!IP4) done('SKIP tcp_rawip NO_IP4');
  httpGet({ protocol: 'http:', hostname: IP4, port: 80, path: '/', timeout: TIMEOUT, headers: { Host: 'example.com' } }, 'tcp_rawip');
} else if (MODE === 'tcp_ipv6') {
  if (!IP6) done('SKIP tcp_ipv6 NO_IP6');
  httpGet({ protocol: 'http:', hostname: IP6, port: 80, path: '/', timeout: TIMEOUT, family: 6, headers: { Host: 'example.com' } }, 'tcp_ipv6');
} else if (MODE === 'udp') {
  // Truy van DNS tho (UDP/53) toi 1.1.1.1 - khong di qua net.Socket, khong di qua dns.lookup.
  const dgram = require('dgram');
  const sock = dgram.createSocket('udp4');
  const q = Buffer.from([
    0x12, 0x34, 0x01, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x07, 0x65, 0x78, 0x61, 0x6d, 0x70, 0x6c, 0x65, 0x03, 0x63, 0x6f, 0x6d, 0x00,
    0x00, 0x01, 0x00, 0x01,
  ]);
  const t = setTimeout(() => { try { sock.close(); } catch (e) {} done('BLOCKED udp TIMEOUT'); }, TIMEOUT);
  sock.on('message', (msg) => { clearTimeout(t); try { sock.close(); } catch (e) {} done('REACHED udp bytes=' + msg.length); });
  sock.on('error', (e) => { clearTimeout(t); try { sock.close(); } catch (e2) {} done('BLOCKED udp ' + (e.code || e.message)); });
  sock.send(q, 53, '1.1.1.1', (e) => { if (e) { clearTimeout(t); done('BLOCKED udp send ' + (e.code || e.message)); } });
} else {
  done('SKIP unknown_mode ' + MODE);
}
