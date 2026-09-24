'use strict';
// Lop PHONG THU THEO CHIEU SAU trong tien trinh — ⛔ KHONG phai ranh gioi.
//
// 🔴 Doc ky truoc khi sua: ranh gioi an ninh la AppContainer
//    (`platform_core/workflow/vo_boc.py`). Tep nay chi lam MOT viec: bien mot
//    piece VIET AU (goi thang mot dich khong qua proxy) tu "het gio sau 130 s"
//    thanh "loi doc duoc trong 1 ms". Mot piece CO Y chi can `spawn` mot tien
//    trinh con la di vong qua toan bo tep nay — do duoc, hai spike lien tiep.
//
// ⭐ Vi sao vá `net.Socket.prototype.connect` chu khong phai undici dispatcher:
//    do that tren ban thu `spike/egress/` (Node v24.17.0, 24/09/2026):
//      - undici global dispatcher: chan `fetch()`, KHONG chan `require('https')`
//        va KHONG chan axios -> tuc khong chan gi, vi axios nam trong phan lon
//        SDK cua piece.
//      - `net.Socket.prototype.connect`: chan 100 % to hop do duoc.
//    Spec §11.2 (ban viet truoc) ghi cach undici; do cho thay no sai.
//
// `dns.lookup` chi la lop PHU (bao loi som hon o buoc phan giai ten). Mot
// piece goi bang IP tran khong di qua no lan nao.

const net = require('net');
const dns = require('dns');

function batDau(proxyHost, proxyPort) {
  const chuHost = String(proxyHost || '127.0.0.1');
  const chuPort = Number(proxyPort || 0);

  const goc = net.Socket.prototype.connect;
  net.Socket.prototype.connect = function (...tham) {
    let host = null;
    let port = null;
    const a0 = tham[0];
    if (a0 && typeof a0 === 'object' && !Array.isArray(a0)) {
      host = a0.host; port = a0.port;
    } else if (typeof a0 === 'number' || /^\d+$/.test(String(a0))) {
      port = Number(a0);
      host = typeof tham[1] === 'string' ? tham[1] : 'localhost';
    }
    const hopLe = (host === chuHost || host === 'localhost')
      && Number(port) === chuPort;
    if (!hopLe) {
      const loi = new Error(
        `EGRESS_CHAN: ${host}:${port} — moi luu luong phai di qua proxy `
        + `${chuHost}:${chuPort} (danh sach mien ap o NGOAI tien trinh nay)`);
      loi.code = 'EGRESS_CHAN';
      // Nem dong bo: nguoi goi la chinh ma piece, va no phai thay loi ngay
      // thay vi mot socket im lang khong bao gio ket noi.
      throw loi;
    }
    return goc.apply(this, tham);
  };

  const gocLookup = dns.lookup;
  dns.lookup = function (hostname, opts, cb) {
    const goiLai = typeof opts === 'function' ? opts : cb;
    if (hostname !== chuHost && hostname !== 'localhost') {
      const loi = new Error(`EGRESS_CHAN_DNS: ${hostname}`);
      loi.code = 'EGRESS_CHAN_DNS';
      return process.nextTick(() => goiLai(loi));
    }
    return gocLookup.apply(this, arguments);
  };
}

module.exports = { batDau };
