// Phuong an (b) mot nua khac: CHI va net.Socket.prototype.connect (khong va dns.lookup).
const net = require('net');

const origConnect = net.Socket.prototype.connect;
net.Socket.prototype.connect = function (...args) {
  let host = 'unknown';
  const opts = args[0];
  if (opts && typeof opts === 'object') {
    host = opts.host || opts.path || JSON.stringify(opts);
  } else if (typeof args[1] === 'string') {
    host = args[1];
  } else if (typeof opts === 'number') {
    host = `port:${opts}`;
  }
  const err = new Error(`EGRESS_BLOCKED:net.Socket.connect:${host}`);
  err.code = 'EGRESS_BLOCKED';
  process.nextTick(() => this.emit('error', err));
  return this;
};

console.error('[preload-socket-only] active (chi net.Socket.prototype.connect)');
