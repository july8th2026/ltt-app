// Phuong an (b) mot nua: CHI va dns.lookup (khong va net.Socket.prototype.connect).
// Gia thuyet can kiem: khong chan duoc request goi thang bang dia chi IP (bo qua DNS).
const dns = require('dns');

function blockedErr(where, host) {
  const err = new Error(`EGRESS_BLOCKED:${where}:${host}`);
  err.code = 'EGRESS_BLOCKED';
  return err;
}

dns.lookup = function (hostname, options, callback) {
  if (typeof options === 'function') callback = options;
  process.nextTick(() => callback(blockedErr('dns.lookup', hostname)));
};

if (dns.promises && dns.promises.lookup) {
  dns.promises.lookup = async function (hostname) {
    throw blockedErr('dns.promises.lookup', hostname);
  };
}

console.error('[preload-dns-only] active (chi dns.lookup)');
